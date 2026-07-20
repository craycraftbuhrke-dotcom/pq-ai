import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.domain import ApiKey, AppUser, Permission, Role, RolePermission, UserRole, UserSession

logger = logging.getLogger(__name__)

# P0-7 未匹配路径的保守兜底：先前是 "process.write"，会让工艺工程师、AI 推荐等多个角色
# 意外获得写权限；改为 "security.manage" 后仅 ADMIN 能通过，未匹配路径会 403 而不是静默放行。
# 同时记录 warning 便于快速发现遗漏的路由映射。集合避免同一路径重复告警刷屏。
_UNMAPPED_WRITE_ROUTES: set[str] = set()


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
    "engineering.manage": "处理工程问题、3C3B 路线与现场协同闭环",
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
        "engineering.manage",
        "features.build",
        "ai.predict",
        "ai.recommend",
    },
    "QUALITY_ENGINEER": {"quality.write", "engineering.manage", "features.build", "ai.predict", "ai.verify"},
    "APPROVER": {"engineering.manage", "ai.approve", "audit.read"},
    "ROBOT_OPERATOR": {"ai.execute"},
    "DATA_SCIENTIST": {"engineering.manage", "features.build", "ai.train", "ai.predict", "ai.recommend"},
    "INTEGRATION_OPERATOR": {"integration.manage", "audit.read"},
    "AUDITOR": {"audit.read"},
}


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000
SESSION_TOKEN_PREFIX = "pqs_"


def hash_api_key(raw_key: str) -> str:
    return sha256(raw_key.encode("utf-8")).hexdigest()


def hash_session_token(raw_token: str) -> str:
    return sha256(raw_token.encode("utf-8")).hexdigest()


def hash_password(raw_password: str) -> str:
    salt = token_urlsafe(16)
    digest = pbkdf2_hmac(
        "sha256",
        raw_password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(raw_password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        scheme, iterations, salt, digest = stored_hash.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        candidate = pbkdf2_hmac(
            "sha256",
            raw_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
    except (ValueError, TypeError):
        return False
    return compare_digest(candidate, digest)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _actor_for_user(db: Session, user: AppUser) -> Actor:
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
    return Actor(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=roles,
        permissions=permissions,
    )


def build_actor_for_user(db: Session, user: AppUser) -> Actor:
    return _actor_for_user(db, user)


def authenticate_password(db: Session, username: str, password: str) -> AppUser | None:
    user = db.scalar(select(AppUser).where(AppUser.username == username))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(UTC)
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    return user


def authenticate_api_key(db: Session, raw_key: str) -> Actor | None:
    if not raw_key:
        return None
    hashed = hash_api_key(raw_key)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hashed, ApiKey.is_active.is_(True)))
    if not api_key or not compare_digest(api_key.key_hash, hashed):
        return None
    now = datetime.now(UTC)
    if api_key.expires_at:
        expires_at = _as_utc(api_key.expires_at)
        if expires_at <= now:
            return None
    user = db.get(AppUser, api_key.user_id)
    if not user or not user.is_active:
        return None
    actor = _actor_for_user(db, user)
    api_key.last_used_at = now
    db.commit()
    return actor


def authenticate_session_token(db: Session, raw_token: str) -> Actor | None:
    if not raw_token:
        return None
    token_hash = hash_session_token(raw_token)
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
    )
    if not session or not compare_digest(session.token_hash, token_hash):
        return None
    now = datetime.now(UTC)
    expires_at = _as_utc(session.expires_at)
    if not expires_at or expires_at <= now:
        return None
    user = db.get(AppUser, session.user_id)
    if not user or not user.is_active:
        return None
    session.last_seen_at = now
    db.commit()
    return _actor_for_user(db, user)


def login_with_password(
    db: Session,
    username: str,
    password: str,
    *,
    user_agent: str | None = None,
    client_ip: str | None = None,
) -> tuple[Actor, str, datetime] | None:
    now = datetime.now(UTC)
    user = db.scalar(select(AppUser).where(AppUser.username == username))
    if not user or not user.is_active:
        return None
    locked_until = _as_utc(user.locked_until)
    if locked_until and locked_until > now:
        return None
    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.login_lockout_threshold:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
        db.commit()
        return None

    raw_token = f"{SESSION_TOKEN_PREFIX}{token_urlsafe(32)}"
    expires_at = now + timedelta(minutes=settings.session_ttl_minutes)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        issued_at=now,
        expires_at=expires_at,
        last_seen_at=now,
        user_agent=user_agent[:500] if user_agent else None,
        client_ip=client_ip,
    )
    db.add(session)
    db.commit()
    return _actor_for_user(db, user), raw_token, expires_at


def revoke_session_token(db: Session, raw_token: str) -> bool:
    if not raw_token:
        return False
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_session_token(raw_token),
            UserSession.revoked_at.is_(None),
        )
    )
    if not session:
        return False
    session.revoked_at = datetime.now(UTC)
    db.commit()
    return True


def required_permission(method: str, path: str) -> str | None:
    if path.startswith("/api/v1/auth/"):
        return None
    if method in {"GET", "HEAD", "OPTIONS"}:
        if path.startswith("/api/v1/audit"):
            return "audit.read"
        if path.startswith("/api/v1/security"):
            return "security.manage"
        if path.startswith("/api/v1/ai/rollback-executions"):
            return "ai.execute"
        return None
    if path.startswith("/api/v1/security"):
        return "security.manage"
    if path.startswith("/api/v1/quality"):
        return "quality.write"
    if path.startswith("/api/v1/features"):
        return "features.build"
    if path.startswith("/api/v1/integrations"):
        return "integration.manage"
    if path.startswith("/api/v1/remote-stations/connections"):
        return "integration.manage"
    if path.startswith("/api/v1/remote-stations/releases"):
        if path.endswith(("/approve", "/reject")):
            return "ai.approve"
        if path.endswith("/commit"):
            return "ai.execute"
        if path.endswith(("/stage", "/refresh", "/verify-readback")):
            return "integration.manage"
        return "process.write"
    if path.startswith("/api/v1/engineering"):
        return "engineering.manage"
    if path.startswith(
        (
            "/api/v1/spray-programs",
            "/api/v1/program-versions",
            "/api/v1/brushes",
            "/api/v1/brush-parameters",
            "/api/v1/parameter-definitions",
            "/api/v1/production-runs",
            "/api/v1/production-stage-runs",
            "/api/v1/actual-parameters",
            "/api/v1/material-batches",
        )
    ):
        return "process.write"
    if path.startswith("/api/v1/bulk/"):
        if path.startswith("/api/v1/bulk/master."):
            return "master.write"
        if path.startswith("/api/v1/bulk/quality.") or path.startswith(
            "/api/v1/bulk/measurement-governance."
        ):
            return "quality.write"
        if path.startswith("/api/v1/bulk/integrations."):
            return "integration.manage"
        if path.startswith("/api/v1/bulk/engineering."):
            return "engineering.manage"
        return "process.write"
    if path in {"/api/v1/ai/models/train", "/api/v1/ai/models/datasets"}:
        return "ai.train"
    if path.startswith("/api/v1/ai/models/training-wide"):
        return "ai.train"
    if path.startswith("/api/v1/ai/models/acceptance-policies"):
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
    if path.endswith("/controlled-trial") and "/api/v1/ai/recommendations/" in path:
        return "ai.approve"
    if path.endswith("/approval") and "/api/v1/ai/controlled-trials/" in path:
        return "ai.approve"
    if path.endswith("/rollback") and "/api/v1/ai/controlled-trials/" in path:
        return "ai.execute"
    if path.startswith("/api/v1/ai/rollback-executions"):
        return "ai.execute"
    if path.startswith("/api/v1/ai/controlled-trials"):
        return "ai.approve"
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
    # 未匹配的写路径：保守兜底为 security.manage（仅 ADMIN 拥有）。
    # 从前的 "process.write" 兜底会让工艺工程师无意中获得非工艺路由的写权限。
    if path not in _UNMAPPED_WRITE_ROUTES:
        _UNMAPPED_WRITE_ROUTES.add(path)
        logger.warning("required_permission fallback: 未识别写路径 %s %s，暂按 security.manage 授权", method, path)
    return "security.manage"


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
