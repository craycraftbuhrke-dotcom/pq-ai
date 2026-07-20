from secrets import token_urlsafe
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    PERMISSION_CATALOG,
    build_actor_for_user,
    hash_api_key,
    hash_password,
    login_with_password,
    revoke_session_token,
    verify_password,
)
from app.db.session import get_db
from app.models.domain import (
    ApiKey,
    AppUser,
    AuditLog,
    Permission,
    Role,
    RolePermission,
    UserSession,
    UserRole,
)
from app.schemas.security import (
    ActorRead,
    ApiKeyCreate,
    ApiKeyIssued,
    AuditLogRead,
    AuditSummary,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    RoleCreate,
    RoleRead,
    UserCreate,
    UserRead,
    UserRoleAssignment,
)

router = APIRouter(tags=["security-audit"])


@router.get("/auth/me", response_model=ActorRead)
def current_actor(request: Request) -> dict:
    actor = request.state.actor
    return {
        "user_id": actor.user_id,
        "username": actor.username,
        "display_name": actor.display_name,
        "roles": list(actor.roles),
        "permissions": sorted(actor.permissions),
        "auth_enabled": settings.api_auth_enabled,
    }


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    result = login_with_password(
        db,
        payload.username,
        payload.password,
        user_agent=request.headers.get("user-agent"),
        client_ip=request.client.host if request.client else None,
    )
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    actor, access_token, expires_at = result
    actor_payload = {
        "user_id": actor.user_id,
        "username": actor.username,
        "display_name": actor.display_name,
        "roles": list(actor.roles),
        "permissions": sorted(actor.permissions),
        "auth_enabled": settings.api_auth_enabled,
    }
    return {
        **actor_payload,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "actor": actor_payload,
    }


@router.post("/auth/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    if not settings.allow_self_registration:
        raise HTTPException(status_code=403, detail="系统未开放自助注册，请联系管理员创建账号")
    if db.scalar(select(AppUser).where(AppUser.username == payload.username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    if payload.email and db.scalar(select(AppUser).where(AppUser.email == payload.email)):
        raise HTTPException(status_code=409, detail="邮箱已被注册")
    user = AppUser(
        username=payload.username,
        display_name=payload.display_name,
        email=payload.email,
        department=payload.department,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    db.commit()
    db.refresh(user)
    result = login_with_password(
        db,
        payload.username,
        payload.password,
    )
    if not result:
        raise HTTPException(status_code=500, detail="注册成功但自动登录失败")
    actor, access_token, expires_at = result
    actor_payload = {
        "user_id": actor.user_id,
        "username": actor.username,
        "display_name": actor.display_name,
        "roles": list(actor.roles),
        "permissions": sorted(actor.permissions),
        "auth_enabled": settings.api_auth_enabled,
    }
    return {
        **actor_payload,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "actor": actor_payload,
    }


@router.put("/auth/me/password")
def change_password(
    payload: PasswordChangeRequest, request: Request, db: Session = Depends(get_db)
) -> dict:
    actor = request.state.actor
    if not actor.user_id:
        raise HTTPException(status_code=401, detail="需要登录后才能修改密码")
    user = db.get(AppUser, actor.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(UTC)
    now = datetime.now(UTC)
    for session in db.scalars(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
    ):
        session.revoked_at = now
    for api_key in db.scalars(
        select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active.is_(True))
    ):
        api_key.is_active = False
    db.commit()
    return {"message": "密码已更新"}


@router.put("/auth/me", response_model=ActorRead)
def update_profile(
    payload: ProfileUpdateRequest, request: Request, db: Session = Depends(get_db)
) -> dict:
    actor = request.state.actor
    if not actor.user_id:
        raise HTTPException(status_code=401, detail="需要登录后才能修改个人信息")
    user = db.get(AppUser, actor.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    updates = payload.model_dump(exclude_none=True)
    if "email" in updates and updates["email"] != user.email:
        if updates["email"] and db.scalar(
            select(AppUser).where(AppUser.email == updates["email"], AppUser.id != user.id)
        ):
            raise HTTPException(status_code=409, detail="邮箱已被其他用户使用")
    for key, value in updates.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    new_actor = build_actor_for_user(db, user)
    return {
        "user_id": new_actor.user_id,
        "username": new_actor.username,
        "display_name": new_actor.display_name,
        "roles": list(new_actor.roles),
        "permissions": sorted(new_actor.permissions),
        "auth_enabled": settings.api_auth_enabled,
    }


@router.post("/auth/logout")
def logout(request: Request, db: Session = Depends(get_db)) -> dict:
    bearer_token = _bearer_token(request.headers.get("authorization", ""))
    if bearer_token:
        revoke_session_token(db, bearer_token)
    api_key_header = request.headers.get("x-api-key", "")
    if api_key_header:
        key_hash = hash_api_key(api_key_header)
        api_key = db.scalar(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        )
        if api_key:
            api_key.is_active = False
            db.commit()
    return {"message": "已退出登录"}


def _bearer_token(header_value: str) -> str:
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return ""
    return token.strip()


@router.get("/security/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[AppUser]:
    return list(db.scalars(select(AppUser).order_by(AppUser.username)))


@router.post("/security/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> AppUser:
    if db.scalar(select(AppUser).where(AppUser.username == payload.username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    values = payload.model_dump(exclude={"password"})
    user = AppUser(**values)
    if payload.password:
        user.password_hash = hash_password(payload.password)
        user.password_changed_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/security/roles", response_model=list[RoleRead])
def list_roles(db: Session = Depends(get_db)) -> list[dict]:
    roles = list(db.scalars(select(Role).order_by(Role.code)))
    return [
        {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "permission_codes": list(
                db.scalars(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .where(RolePermission.role_id == role.id)
                    .order_by(Permission.code)
                )
            ),
        }
        for role in roles
    ]


@router.post("/security/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(Role).where(Role.code == payload.code)):
        raise HTTPException(status_code=409, detail="角色代码已存在")
    unknown = set(payload.permission_codes) - set(PERMISSION_CATALOG)
    if unknown:
        raise HTTPException(status_code=422, detail=f"未知权限：{', '.join(sorted(unknown))}")
    role = Role(code=payload.code, name=payload.name, description=payload.description)
    db.add(role)
    db.flush()
    permissions = list(
        db.scalars(select(Permission).where(Permission.code.in_(payload.permission_codes)))
    )
    db.add_all(
        [RolePermission(role_id=role.id, permission_id=permission.id) for permission in permissions]
    )
    db.commit()
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "permission_codes": sorted(payload.permission_codes),
    }


@router.post("/security/users/{user_id}/roles")
def assign_user_role(
    user_id: str, payload: UserRoleAssignment, db: Session = Depends(get_db)
) -> dict:
    user = db.get(AppUser, user_id)
    role = db.scalar(select(Role).where(Role.code == payload.role_code))
    if not user or not role:
        raise HTTPException(status_code=404, detail="用户或角色不存在")
    existing = db.scalar(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    )
    if not existing:
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
    return {"user_id": user.id, "role_code": role.code, "assigned": True}


@router.get("/security/users/{user_id}/api-keys/list", response_model=list[dict])
def list_api_keys(user_id: str, db: Session = Depends(get_db)) -> list[dict]:
    if not db.get(AppUser, user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    keys = list(
        db.scalars(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
    )
    return [
        {
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "expires_at": key.expires_at,
            "last_used_at": key.last_used_at,
            "is_active": key.is_active,
        }
        for key in keys
    ]


@router.post(
    "/security/users/{user_id}/api-keys",
    response_model=ApiKeyIssued,
    status_code=status.HTTP_201_CREATED,
)
def issue_api_key(user_id: str, payload: ApiKeyCreate, db: Session = Depends(get_db)) -> dict:
    if not db.get(AppUser, user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    raw_key = f"pq_{token_urlsafe(32)}"
    api_key = ApiKey(
        user_id=user_id,
        name=payload.name,
        key_prefix=raw_key[:12],
        key_hash=hash_api_key(raw_key),
        expires_at=payload.expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "raw_key": raw_key,
        "expires_at": api_key.expires_at,
    }


@router.get("/audit/logs", response_model=list[AuditLogRead])
def list_audit_logs(limit: int = 100, db: Session = Depends(get_db)) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .order_by(AuditLog.occurred_at.desc())
            .limit(min(max(limit, 1), 500))
        )
    )


@router.get("/audit/summary", response_model=AuditSummary)
def audit_summary(db: Session = Depends(get_db)) -> dict:
    events_by_action = {
        action: count
        for action, count in db.execute(
            select(AuditLog.action, func.count()).group_by(AuditLog.action)
        )
    }
    return {
        "total_events": int(db.scalar(select(func.count()).select_from(AuditLog)) or 0),
        "successful_writes": int(
            db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.status_code < 400)
            )
            or 0
        ),
        "failed_writes": int(
            db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.status_code >= 400)
            )
            or 0
        ),
        "active_users": int(
            db.scalar(select(func.count()).select_from(AppUser).where(AppUser.is_active.is_(True)))
            or 0
        ),
        "active_api_keys": int(
            db.scalar(select(func.count()).select_from(ApiKey).where(ApiKey.is_active.is_(True)))
            or 0
        ),
        "events_by_action": events_by_action,
    }
