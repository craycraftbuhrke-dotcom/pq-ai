from sqlalchemy.engine import Engine

from app.db.base import Base


def create_transient_test_schema(engine: Engine) -> None:
    """Create schema only for isolated SQLite test databases.

    Production and shared MySQL schema changes are forbidden in application code.
    They must be approved by ticket and executed manually by the database owner.
    """
    if engine.url.get_backend_name() != "sqlite":
        raise AssertionError("Test schema bootstrap is allowed only for transient SQLite databases")
    Base.metadata.create_all(engine)
