from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# MySQL 上给一个短的连接超时（3s），避免启动阶段 (lifespan/startup_seed) 因 MySQL
# 尚未就绪而挂住 K8s startupProbe 的 failureThreshold 触发 CrashLoop。SQLite
# 不支持该参数，因此按 URL scheme 条件添加。
_connect_args: dict = {}
if settings.database_url.startswith(("mysql", "mariadb")):
    _connect_args["connect_timeout"] = 3

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

FORBIDDEN_MYSQL_RUNTIME_PREFIXES = ("delete", "create", "drop", "alter", "truncate", "replace")


class DatabaseOperationPolicyError(RuntimeError):
    pass


@event.listens_for(engine, "before_cursor_execute")
def enforce_mysql_operation_policy(conn, cursor, statement, parameters, context, executemany) -> None:
    if conn.dialect.name not in {"mysql", "mariadb"}:
        return
    sql = statement.lstrip().lower()
    if not sql:
        return
    first_token = sql.split(None, 1)[0]
    if first_token in FORBIDDEN_MYSQL_RUNTIME_PREFIXES:
        raise DatabaseOperationPolicyError(
            f"MySQL runtime SQL '{first_token.upper()}' is forbidden by company policy; "
            "schema changes require DBA approval and physical deletes must be replaced "
            "by status/version workflows."
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
