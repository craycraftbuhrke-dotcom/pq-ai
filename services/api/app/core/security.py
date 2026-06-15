from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import ApiKey, AppUser, Permission, Role, RolePermission, UserRole


@dataclass(frozen=True)
class Actor:
    user_id: str | None
    username: str
    display_name: str
    roles: tuple[str, ...]
    permissions: frozenset[str]

    def can(self, permission: str | None) -> bool:
        return permission is None or "*" in self.permissions or permission in self.permissions


SYSTEM_ACTOR = Actor(
    user_id=None,
    username="system",
    display_name="系统开发模式",
    roles=("SYSTEM",),
    permissions=frozenset({"*"}),
)

ANONYMOUS_ACTOR = Actor(
    user_id=None,
    username="anonymous",
    display_name="未认证请求",
    roles=(),
    permissions=frozenset(),
)


PERMISSION_CATALOG = {
    "security.manage": "安全用户、角色与密钥管理",
    "audit.read": "查看审计日志",
    "master.write": "维护主数据",
    "process.write": "维护程序、刷子与生产实绩",
    "quality.write": "导入质量数据与维护标准",
    "features.build": "构建点位特征快照",
    "ai.train": "训练和注册模型",
    "ai.predict": "执行预测与诊断",
    "ai.recommend": "生成参数推荐",
    "ai.approve": "审批参数推荐",
    "ai.execute": "记录推荐执行",
    "ai.verify": "完成复测效果评价",
    "integration.manage": "管理外部系统集成与事件重放",
}


ROLE_CATALOG = {
    "ADMIN": set(PERMISSION_CATALOG),
    "PROCESS_ENGINEER": {
        "master.write",
        "process.write",
        "features.build",
        "ai.predict",
        "ai.recommend",
    },
    "QUALITY_ENGINEER": {"quality.write", "features.build", "ai.predict", "ai.verify"},
    "APPROVER": {"ai.approve", "audit.read"},
    "ROBOT_OPERATOR": {"ai.execute"},
    "DATA_SCIENTIST": {"features.build", "ai.train", "ai.predict", "ai.recommend"},
    "INTEGRATION_OPERATOR": {"integration.manage", "audit.read"},
    "AUDITOR": {"audit.read"},
}


def hash_api_key(raw_key: str) -> str:
    return sha256(raw_key.encode("utf-8")).hexdigest()


def authenticate_api_key(db: Session, raw_key: str) -> Actor | None:
    if not raw_key:
        return None
    hashed = hash_api_key(raw_key)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hashed, ApiKey.is_active.is_(True)))
    if not api_key or not compare_digest(api_key.key_hash, hashed):
        return None
    now = datetime.now(UTC)
    if api_key.expires_at:
        expires_at = api_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            return None
    user = db.get(AppUser, api_key.user_id)
    if not user or not user.is_active:
        return None
    roles = tuple(
        db.scalars(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
            .order_by(Role.code)
        )
    )
    permissions = frozenset(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user.id)
        )
    )
    api_key.last_used_at = now
    db.commit()
    return Actor(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=roles,
        permissions=permissions,
    )


def required_permission(method: str, path: str) -> str | None:
    if method in {"GET", "HEAD", "OPTIONS"}:
        if path.startswith("/api/v1/audit"):
            return "audit.read"
        if path.startswith("/api/v1/security"):
            return "security.manage"
        return None
    if path.startswith("/api/v1/security"):
        return "security.manage"
    if path.startswith("/api/v1/quality"):
        return "quality.write"
    if path.startswith("/api/v1/features"):
        return "features.build"
    if path.startswith("/api/v1/integrations"):
        return "integration.manage"
    if path in {"/api/v1/ai/models/train", "/api/v1/ai/models/datasets"}:
        return "ai.train"
    if "/ai/models/" in path and path.endswith(
        ("/status", "/acceptance", "/ood-policy", "/applicability-scopes")
    ):
        return "ai.train"
    if "/ai/models/" in path and "/applicability-scopes/" in path:
        return "ai.train"
    if "/ai/models/" in path and path.endswith("/recommendations"):
        return "ai.recommend"
    if "/ai/models/" in path or path.startswith("/api/v1/ai/predictions") or path.startswith(
        "/api/v1/ai/diagnoses"
    ):
        return "ai.predict"
    if path.endswith("/approval") and "/api/v1/ai/recommendations/" in path:
        return "ai.approve"
    if path.endswith("/execution") and "/api/v1/ai/recommendations/" in path:
        return "ai.execute"
    if path.endswith("/verification") and "/api/v1/ai/recommendations/" in path:
        return "ai.verify"
    if path.startswith("/api/v1/ai/recommendations"):
        return "ai.recommend"
    if path.startswith(
        (
            "/api/v1/factories",
            "/api/v1/vehicle-models",
            "/api/v1/colors",
            "/api/v1/parts",
            "/api/v1/factory-vehicle-models",
            "/api/v1/vehicle-model-colors",
            "/api/v1/measurement-groups",
            "/api/v1/measurement-points",
        )
    ):
        return "master.write"
    return "process.write"


def resource_from_path(path: str) -> tuple[str | None, str | None]:
    segments = [segment for segment in path.removeprefix("/api/v1/").split("/") if segment]
    if not segments:
        return None, None
    resource_type = segments[0].replace("-", "_")
    resource_id = segments[1] if len(segments) > 1 and segments[1] not in {
        "train",
        "summary",
        "measurements",
        "standards",
        "metric-definitions",
        "point-snapshots",
    } else None
    return resource_type, resource_id
