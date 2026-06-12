from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import PERMISSION_CATALOG, hash_api_key
from app.db.session import get_db
from app.models.domain import (
    ApiKey,
    AppUser,
    AuditLog,
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from app.schemas.security import (
    ActorRead,
    ApiKeyCreate,
    ApiKeyIssued,
    AuditLogRead,
    AuditSummary,
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


@router.get("/security/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[AppUser]:
    return list(db.scalars(select(AppUser).order_by(AppUser.username)))


@router.post("/security/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> AppUser:
    if db.scalar(select(AppUser).where(AppUser.username == payload.username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = AppUser(**payload.model_dump())
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
