from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from tests.schema_guard import create_transient_test_schema
from app.models import domain  # noqa: F401
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
from app.services.quality_evaluation import evaluate_quality_measurement


def test_quality_evaluation_prefers_point_standard_and_detects_violation() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_transient_test_schema(engine)
    now = datetime.now(UTC)
    with Session(engine, expire_on_commit=False) as db:
        factory = Factory(code="F1", name="工厂")
        model = VehicleModel(code="M1", name="车型")
        color = Color(code="C1", name="颜色", color_type="BASECOAT")
        part = Part(code="ROOF", name="车顶")
        db.add_all([factory, model, color, part])
        db.flush()
        point = MeasurementPoint(
            code="P1",
            name="点位",
            vehicle_model_id=model.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        )
        run = ProductionRun(
            run_no="RUN-1",
            factory_id=factory.id,
            vehicle_model_id=model.id,
            color_id=color.id,
            started_at=now,
        )
        db.add_all([point, run])
        db.flush()
        measurement = QualityMeasurement(
            data_no="QM-1",
            production_run_id=run.id,
                measurement_point_id=point.id,
                quality_type="ORANGE_PEEL",
                measured_at=now,
                reliability_status="VERIFIED",
        )
        db.add(measurement)
        db.flush()
        metric = QualityMetricValue(
            measurement_id=measurement.id,
            metric_code="doi",
            metric_name="DOI",
            raw_value=80.0,
        )
        db.add_all(
            [
                metric,
                QualityStandard(
                    standard_no="GLOBAL",
                    version="1",
                    quality_type="ORANGE_PEEL",
                    metric_code="doi",
                    min_value=75.0,
                ),
                QualityStandard(
                    standard_no="POINT",
                    version="1",
                    quality_type="ORANGE_PEEL",
                    metric_code="doi",
                    measurement_point_id=point.id,
                    min_value=82.0,
                ),
            ]
        )
        db.commit()

        result = evaluate_quality_measurement(db, measurement, [metric])

        assert result["judgement"] == "FAIL"
        assert result["metric_results"][0]["standard_no"] == "POINT"
        assert result["violations"] == ["DOI 80，要求 ≥ 82.0"]
