from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.factories import create_factory
from app.api.routes.master_data import (
    bind_factory_vehicle_model,
    bind_vehicle_model_color,
    create_color,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.api.routes.measurement_governance import (
    create_instrument,
    measurement_governance_summary,
    update_instrument,
)
from app.api.routes.process import create_production_run
from app.api.routes.quality import create_quality_measurement, get_quality_measurement
from app.models.domain import MeasurementInstrument, QualityMeasurement, QualityMetricValue
from app.schemas.common import FactoryCreate
from app.schemas.master_data import (
    ColorCreate,
    FactoryVehicleModelCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelColorCreate,
    VehicleModelCreate,
)
from app.schemas.process import ProductionRunCreate
from app.schemas.quality import (
    MeasurementInstrumentCreate,
    MeasurementInstrumentUpdate,
    QualityMeasurementCreate,
    QualityMetricInput,
)
from app.services.measurement_reliability import refresh_measurement_reliability
from tests.schema_guard import create_transient_test_schema


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def _seed_context(db: Session, suffix: str):
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code=f"F-{suffix}", name=f"工厂{suffix}"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code=f"M-{suffix}", name=f"车型{suffix}"), db)
    color = create_color(
        ColorCreate(code=f"C-{suffix}", name=f"颜色{suffix}", color_type="BASECOAT"),
        db,
    )
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle.id),
        db,
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle.id, color_id=color.id),
        db,
    )
    part = create_part(PartCreate(code=f"P-{suffix}", name="车顶"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code=f"PT-{suffix}",
            name="车顶点位",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL", "THICKNESS", "COLOR_DIFFERENCE"],
        ),
        db,
    )
    run = create_production_run(
        ProductionRunCreate(
            run_no=f"RUN-{suffix}",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    return now, run, point


def test_lean_reliability_accepts_upload_without_provenance() -> None:
    """Day-1: quality upload without instrument/method/calibration is VERIFIED."""
    db = build_session()
    now, run, point = _seed_context(db, "LEAN")
    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-LEAN",
            production_run_id=run.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=80.0)],
        ),
        db,
    )
    assert measurement["reliability_status"] == "VERIFIED"
    assert measurement["reliability_issues"] == []
    assert measurement["judgement"] != "INVALID"
    db.close()


def test_lean_reliability_fails_only_when_instrument_inactive() -> None:
    db = build_session()
    now, run, point = _seed_context(db, "OFF")
    instrument = create_instrument(
        MeasurementInstrumentCreate(
            code="BYK-OFF",
            name="停用橘皮仪",
            manufacturer="BYK",
            model="wave-scan",
            instrument_type="BYK_ORANGE_PEEL",
            serial_no="SN-OFF",
            supported_quality_types=["ORANGE_PEEL"],
            calibration_required=False,
        ),
        db,
    )
    update_instrument(
        instrument.id,
        MeasurementInstrumentUpdate(status="RETIRED"),
        db,
    )
    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-OFF",
            production_run_id=run.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            instrument_id=instrument.id,
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=81.0)],
        ),
        db,
    )
    assert measurement["reliability_status"] == "FAILED"
    assert measurement["judgement"] == "INVALID"
    assert any("停用" in issue for issue in measurement["reliability_issues"])
    db.close()


def test_lean_reliability_ignores_calibration_method_and_profile_gaps() -> None:
    """Historical strict provenance gaps no longer fail or leave rows unverified."""
    db = build_session()
    now = datetime.now(UTC)
    instrument = MeasurementInstrument(
        code="FISCHER-LEAN",
        name="Fischer",
        manufacturer="Helmut Fischer",
        model="Dualscope",
        instrument_type="FISCHER_THICKNESS",
        serial_no="SN-LEAN",
        supported_quality_types=["THICKNESS"],
        calibration_required=True,
        status="ACTIVE",
    )
    db.add(instrument)
    db.flush()
    measurement = QualityMeasurement(
        data_no="QM-LEAN-LAYER",
        production_run_id="run-lean",
        measurement_point_id="point-lean",
        quality_type="THICKNESS",
        data_type="TEST",
        measured_at=now,
        instrument_id=instrument.id,
        is_valid=True,
    )
    db.add(measurement)
    db.flush()
    db.add(
        QualityMetricValue(
            measurement_id=measurement.id,
            metric_code="thickness_midcoat",
            metric_name="中涂膜厚",
            raw_value=30.0,
        )
    )
    db.flush()
    status, issues = refresh_measurement_reliability(db, measurement)
    assert status == "VERIFIED"
    assert issues == []
    assert measurement_governance_summary(db)["instruments"] >= 1
    db.close()


def test_self_heal_reclassifies_legacy_unverified_on_read() -> None:
    db = build_session()
    now, run, point = _seed_context(db, "HEAL")
    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-HEAL",
            production_run_id=run.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=79.0)],
        ),
        db,
    )
    # Simulate a legacy row stamped under the old strict policy.
    entity = db.get(QualityMeasurement, measurement["id"])
    assert entity is not None
    entity.reliability_status = "UNVERIFIED"
    entity.reliability_issues = ["缺少受治理测量仪器", "缺少受治理测量方法"]
    db.flush()

    healed = get_quality_measurement(measurement["id"], db)
    assert healed["reliability_status"] == "VERIFIED"
    assert healed["reliability_issues"] == []
    assert healed["judgement"] != "INVALID"
    db.close()
