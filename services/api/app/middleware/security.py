from time import perf_counter
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database_errors import database_error_response
from app.core.security import (
    ANONYMOUS_ACTOR,
    SYSTEM_ACTOR,
    authenticate_api_key,
    authenticate_session_token,
    required_permission,
    resource_from_path,
)
from app.db.session import SessionLocal
from app.models.domain import AuditLog


EXEMPT_PATHS = {
    "/",
    "/docs",
    "/openapi.json",
    f"{settings.api_prefix}/health",
    f"{settings.api_prefix}/health/live",
    f"{settings.api_prefix}/health/ready",
    f"{settings.api_prefix}/auth/login",
    f"{settings.api_prefix}/auth/register",
}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def security_and_audit_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    path = request.url.path
    # 公开端点也必须按匿名身份审计；只有显式关闭认证的隔离测试使用系统身份。
    actor = ANONYMOUS_ACTOR
    if not settings.api_auth_enabled:
        actor = SYSTEM_ACTOR

    if settings.api_auth_enabled and path not in EXEMPT_PATHS and request.method != "OPTIONS":
        bearer_token = _bearer_token(request.headers.get("authorization", ""))
        raw_key = request.headers.get("x-api-key", "")
        try:
            with SessionLocal() as db:
                actor = (
                    authenticate_session_token(db, bearer_token)
                    if bearer_token
                    else authenticate_api_key(db, raw_key)
                )
        except SQLAlchemyError as exc:
            return database_error_response(exc, request_id)
        if not actor:
            if request.method in WRITE_METHODS and path.startswith(settings.api_prefix):
                _write_audit(request, ANONYMOUS_ACTOR, request_id, 401, 0)
            return JSONResponse(
                status_code=401,
                content={"detail": "登录会话或系统接口密钥无效或已过期", "request_id": request_id},
                headers={"x-request-id": request_id},
            )
        permission = required_permission(request.method, path)
        if not actor.can(permission):
            if request.method in WRITE_METHODS and path.startswith(settings.api_prefix):
                _write_audit(request, actor, request_id, 403, 0)
            return JSONResponse(
                status_code=403,
                content={"detail": f"缺少权限：{permission}", "request_id": request_id},
                headers={"x-request-id": request_id},
            )

    if request.method == "DELETE" and path.startswith(settings.api_prefix):
        _write_audit(request, actor, request_id, 405, 0)
        return JSONResponse(
            status_code=405,
            content={
                "detail": "公司 MySQL 规范禁止物理 DELETE；请使用停用、归档或版本替换流程",
                "request_id": request_id,
            },
            headers={"x-request-id": request_id},
        )

    request.state.actor = actor
    started = perf_counter()
    try:
        response = await call_next(request)
    except SQLAlchemyError as exc:
        if request.method in WRITE_METHODS:
            _write_audit(request, actor, request_id, 500, perf_counter() - started)
        return database_error_response(exc, request_id)
    except Exception:
        if request.method in WRITE_METHODS:
            _write_audit(request, actor, request_id, 500, perf_counter() - started)
        raise
    response.headers["x-request-id"] = request_id
    if request.method in WRITE_METHODS and path.startswith(settings.api_prefix):
        _write_audit(request, actor, request_id, response.status_code, perf_counter() - started)
    return response


def _write_audit(request: Request, actor, request_id: str, status_code: int, duration: float) -> None:
    resource_type, resource_id = resource_from_path(request.url.path)
    try:
        with SessionLocal() as db:
            db.add(
                AuditLog(
                    request_id=request_id,
                    actor_user_id=actor.user_id,
                    actor_username=actor.username,
                    action=required_permission(request.method, request.url.path) or "write",
                    http_method=request.method,
                    path=request.url.path,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    status_code=status_code,
                    client_ip=request.client.host if request.client else None,
                    detail={"duration_ms": round(duration * 1000, 2)},
                )
            )
            db.commit()
    except Exception:
        # Audit failures must not hide the original business response.
        return


def _bearer_token(header_value: str) -> str:
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return ""
    return token.strip()
