from time import perf_counter
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.config import settings
from app.core.security import (
    ANONYMOUS_ACTOR,
    SYSTEM_ACTOR,
    authenticate_api_key,
    required_permission,
    resource_from_path,
)
from app.db.session import SessionLocal
from app.models.domain import AuditLog


EXEMPT_PATHS = {"/", "/docs", "/openapi.json", "/api/v1/health"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def security_and_audit_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    path = request.url.path
    actor = SYSTEM_ACTOR

    if settings.api_auth_enabled and path not in EXEMPT_PATHS and request.method != "OPTIONS":
        raw_key = request.headers.get("x-api-key", "")
        with SessionLocal() as db:
            actor = authenticate_api_key(db, raw_key)
        if not actor:
            if request.method in WRITE_METHODS and path.startswith(settings.api_prefix):
                _write_audit(request, ANONYMOUS_ACTOR, request_id, 401, 0)
            return JSONResponse(
                status_code=401,
                content={"detail": "无效或已过期的 API Key", "request_id": request_id},
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

    request.state.actor = actor
    started = perf_counter()
    try:
        response = await call_next(request)
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
                    detail={
                        "query": str(request.url.query) or None,
                        "duration_ms": round(duration * 1000, 2),
                    },
                )
            )
            db.commit()
    except Exception:
        # Audit failures must not hide the original business response.
        return
