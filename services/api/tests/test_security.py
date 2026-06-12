from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import authenticate_api_key, hash_api_key, required_permission
from app.db.base import Base
from app.models.domain import ApiKey, AppUser, Permission, Role, RolePermission, UserRole


def build_security_session() -> tuple[Session, str]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    permission = Permission(code="quality.write", name="维护质量数据")
    role = Role(code="QUALITY_ENGINEER", name="质量工程师")
    user = AppUser(username="quality.user", display_name="质量工程师")
    db.add_all([permission, role, user])
    db.flush()
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id),
            RolePermission(role_id=role.id, permission_id=permission.id),
        ]
    )
    raw_key = "pq-test-quality-key"
    db.add(
        ApiKey(
            user_id=user.id,
            name="质量测试密钥",
            key_prefix=raw_key[:12],
            key_hash=hash_api_key(raw_key),
        )
    )
    db.commit()
    return db, raw_key


def test_api_key_authentication_resolves_roles_and_permissions() -> None:
    db, raw_key = build_security_session()
    actor = authenticate_api_key(db, raw_key)
    assert actor is not None
    assert actor.username == "quality.user"
    assert actor.roles == ("QUALITY_ENGINEER",)
    assert actor.can("quality.write")
    assert not actor.can("security.manage")
    assert authenticate_api_key(db, "wrong-key") is None
    db.close()


def test_expired_api_key_is_rejected() -> None:
    db, raw_key = build_security_session()
    api_key = db.query(ApiKey).one()
    api_key.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert authenticate_api_key(db, raw_key) is None
    db.close()


def test_endpoint_permissions_cover_security_and_closed_loop_actions() -> None:
    assert required_permission("GET", "/api/v1/security/users") == "security.manage"
    assert required_permission("GET", "/api/v1/audit/logs") == "audit.read"
    assert required_permission("POST", "/api/v1/quality/measurements") == "quality.write"
    assert required_permission("POST", "/api/v1/integrations/events") == "integration.manage"
    assert required_permission("PATCH", "/api/v1/ai/models/model-1/status") == "ai.train"
    assert (
        required_permission("POST", "/api/v1/ai/recommendations/rec-1/approval")
        == "ai.approve"
    )
    assert (
        required_permission("POST", "/api/v1/ai/recommendations/rec-1/execution")
        == "ai.execute"
    )
    assert (
        required_permission("POST", "/api/v1/ai/recommendations/rec-1/verification")
        == "ai.verify"
    )
