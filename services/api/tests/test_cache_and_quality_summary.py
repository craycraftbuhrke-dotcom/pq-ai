from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.quality import QUALITY_SUMMARY_CACHE_KEY, quality_summary
from app.core.cache import cache_delete, cache_get, cache_set
from app.core.security import (
    Actor,
    _actor_cache_key,
    _actor_from_cache,
    _actor_to_cache,
    hash_session_token,
)
from app.models.domain import (
    Color,
    Factory,
    MeasurementPoint,
    Part,
    ProductionRun,
    QualityMeasurement,
    QualityMetricValue,
    QualityStandard,
    VehicleModel,
)
from tests.schema_guard import create_transient_test_schema


def test_memory_cache_roundtrip() -> None:
    cache_delete("test:key")
    assert cache_get("test:key") is None
    cache_set("test:key", {"ok": True}, ttl_seconds=30)
    assert cache_get("test:key") == {"ok": True}
    cache_delete("test:key")
    assert cache_get("test:key") is None


def test_actor_cache_serialization() -> None:
    actor = Actor(
        user_id="u1",
        username="alice",
        display_name="Alice",
        roles=("ADMIN",),
        permissions=frozenset({"ai.train", "*"}),
    )
    payload = _actor_to_cache(actor)
    restored = _actor_from_cache(payload)
    assert restored.username == "alice"
    assert "*" in restored.permissions
    assert _actor_cache_key(hash_session_token("pqs_x"))


def test_quality_summary_uses_sql_aggregates_and_cache() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_transient_test_schema(engine)
    now = datetime.now(UTC)
    cache_delete(QUALITY_SUMMARY_CACHE_KEY)
    with Session(engine, expire_on_commit=False) as db:
        factory = Factory(code="QF1", name="工厂")
        model = VehicleModel(code="QM1", name="车型")
        color = Color(code="QC1", name="颜色", color_type="BASECOAT")
        part = Part(code="QROOF", name="车顶")
        db.add_all([factory, model, color, part])
        db.flush()
        point = MeasurementPoint(
            code="QP1",
            name="点位",
            vehicle_model_id=model.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        )
        db.add(point)
        db.flush()
        run = ProductionRun(
            run_no="QRUN-1",
            factory_id=factory.id,
            vehicle_model_id=model.id,
            color_id=color.id,
            started_at=now,
        )
        db.add(run)
        db.flush()
        measurement = QualityMeasurement(
            data_no="QQM-1",
            production_run_id=run.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            reliability_status="VERIFIED",
            is_valid=True,
        )
        db.add(measurement)
        db.flush()
        db.add(
            QualityMetricValue(
                measurement_id=measurement.id,
                metric_code="doi",
                metric_name="DOI",
                raw_value=85.0,
            )
        )
        db.add(
            QualityStandard(
                standard_no="QS-1",
                quality_type="ORANGE_PEEL",
                metric_code="doi",
                min_value=80.0,
                max_value=100.0,
                is_active=True,
                version="1.0",
            )
        )
        db.commit()

        first = quality_summary(db)
        assert first["measurements"] == 1
        assert first["verified_measurements"] == 1
        assert first["metric_values"] == 1
        assert first["pass_measurements"] == 1
        assert cache_get(QUALITY_SUMMARY_CACHE_KEY) == first

        # Cached path should not require a live session mutation.
        second = quality_summary(db)
        assert second == first
