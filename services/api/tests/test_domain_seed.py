"""领域演示种子：每模型 5 条，且只写入一次。"""

from __future__ import annotations

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.domain import Factory, ProductionRun, SprayProgram, VehicleModel
from app.services.catalog_seed import seed_parameter_catalog, seed_quality_metric_catalog
from app.services.domain_seed import SEED_MARKER_FACTORY_CODE, seed_domain_demo_data
from tests.schema_guard import create_transient_test_schema


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_transient_test_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_domain_seed_writes_five_per_model_once() -> None:
    db = _session()
    try:
        seed_quality_metric_catalog(db)
        seed_parameter_catalog(db)

        first = seed_domain_demo_data(db)
        assert first["skipped"] is False
        assert first["rows_per_model"] == 5
        assert first["created"] > 0
        assert db.scalar(select(func.count()).select_from(Factory)) == 5
        assert db.scalar(select(func.count()).select_from(VehicleModel)) == 5
        assert db.scalar(select(func.count()).select_from(SprayProgram)) == 5
        assert db.scalar(select(func.count()).select_from(ProductionRun)) == 5
        assert (
            db.scalar(select(Factory).where(Factory.code == SEED_MARKER_FACTORY_CODE)) is not None
        )

        second = seed_domain_demo_data(db)
        assert second["skipped"] is True
        assert second["created"] == 0
        assert db.scalar(select(func.count()).select_from(Factory)) == 5
        assert db.scalar(select(func.count()).select_from(ProductionRun)) == 5
    finally:
        db.close()
