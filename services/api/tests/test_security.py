from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import (
    authenticate_api_key,
    authenticate_session_token,
    hash_api_key,
    hash_password,
    login_with_password,
    required_permission,
    revoke_session_token,
)
from tests.schema_guard import create_transient_test_schema
from app.models.domain import ApiKey, AppUser, Permission, Role, RolePermission, UserRole


def build_security_session() -> tuple[Session, str]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
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
    raw_key = f"pq_{token_urlsafe(32)}"
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
    invalid_key = f"pq_{token_urlsafe(32)}"
    actor = authenticate_api_key(db, raw_key)
    assert actor is not None
    assert actor.username == "quality.user"
    assert actor.roles == ("QUALITY_ENGINEER",)
    assert actor.can("quality.write")
    assert not actor.can("security.manage")
    assert authenticate_api_key(db, invalid_key) is None
    db.close()


def test_password_login_issues_and_revokes_user_session() -> None:
    db, _raw_key = build_security_session()
    user = db.query(AppUser).one()
    raw_password = token_urlsafe(32)
    user.password_hash = hash_password(raw_password)
    db.commit()

    login = login_with_password(
        db,
        "quality.user",
        raw_password,
        user_agent="pytest",
        client_ip="127.0.0.1",
    )

    assert login is not None
    actor, raw_token, expires_at = login
    assert actor.username == "quality.user"
    assert raw_token.startswith("pqs_")
    assert expires_at > datetime.now(UTC)

    session_actor = authenticate_session_token(db, raw_token)
    assert session_actor is not None
    assert session_actor.can("quality.write")

    assert revoke_session_token(db, raw_token)
    assert authenticate_session_token(db, raw_token) is None
    db.close()


def test_failed_password_login_increments_counter() -> None:
    db, _raw_key = build_security_session()
    user = db.query(AppUser).one()
    raw_password = token_urlsafe(32)
    invalid_password = token_urlsafe(32)
    user.password_hash = hash_password(raw_password)
    db.commit()

    assert login_with_password(db, "quality.user", invalid_password) is None
    db.refresh(user)
    assert user.failed_login_count == 1
    db.close()


def test_expired_api_key_is_rejected() -> None:
    db, raw_key = build_security_session()
    api_key = db.query(ApiKey).one()
    api_key.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert authenticate_api_key(db, raw_key) is None
    db.close()


def test_endpoint_permissions_cover_security_and_closed_loop_actions() -> None:
    assert required_permission("POST", "/api/v1/auth/login") is None
    assert required_permission("POST", "/api/v1/auth/logout") is None
    assert required_permission("GET", "/api/v1/security/users") == "security.manage"
    assert required_permission("GET", "/api/v1/audit/logs") == "audit.read"
    assert required_permission("POST", "/api/v1/quality/measurements") == "quality.write"
    assert required_permission("POST", "/api/v1/integrations/events") == "integration.manage"
    assert required_permission("POST", "/api/v1/engineering/issue-tasks") == "engineering.manage"
    assert (
        required_permission("POST", "/api/v1/bulk/engineering.issue-tasks/import")
        == "engineering.manage"
    )
    assert required_permission("PATCH", "/api/v1/ai/models/model-1/status") == "ai.train"
    assert required_permission("POST", "/api/v1/ai/models/datasets") == "ai.train"
    assert required_permission("POST", "/api/v1/ai/models/model-1/acceptance") == "ai.train"
    assert (
        required_permission("POST", "/api/v1/ai/models/acceptance-policies")
        == "ai.train"
    )
    assert required_permission("PUT", "/api/v1/ai/models/model-1/ood-policy") == "ai.train"
    assert (
        required_permission("POST", "/api/v1/ai/models/model-1/applicability-scopes")
        == "ai.train"
    )
    assert (
        required_permission("POST", "/api/v1/ai/recommendations/rec-1/approval")
        == "ai.approve"
    )
    assert (
        required_permission("POST", "/api/v1/ai/recommendations/rec-1/controlled-trial")
        == "ai.approve"
    )
    assert (
        required_permission("POST", "/api/v1/ai/controlled-trials/trial-1/approval")
        == "ai.approve"
    )
    assert (
        required_permission("POST", "/api/v1/ai/recommendations/rec-1/execution")
        == "ai.execute"
    )
    assert (
        required_permission("POST", "/api/v1/ai/controlled-trials/trial-1/rollback")
        == "ai.execute"
    )
    assert required_permission("GET", "/api/v1/ai/rollback-executions") == "ai.execute"
    assert (
        required_permission("POST", "/api/v1/ai/recommendations/rec-1/verification")
        == "ai.verify"
    )
