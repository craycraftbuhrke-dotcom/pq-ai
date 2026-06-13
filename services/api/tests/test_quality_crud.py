from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.api.routes.factories import create_factory
from app.api.routes.master_data import (
    create_color,
    create_measurement_group,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.api.routes.process import create_production_run
from app.api.routes.quality import (
    create_quality_measurement,
    create_quality_standard,
    delete_quality_measurement,
    delete_quality_standard,
    get_quality_measurement,
    get_quality_standard,
    quality_analytics,
    update_quality_measurement,
    update_quality_standard,
)
from app.db.base import Base
from app.models.domain import (
    MeasurementCalibrationRecord,
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementReferenceStandard,
)
from app.schemas.common import FactoryCreate
from app.schemas.master_data import (
    ColorCreate,
    MeasurementGroupCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelCreate,
)
from app.schemas.process import ProductionRunCreate
from app.schemas.quality import (
    MeasurementRepeatInput,
    QualityMeasurementCreate,
    QualityMeasurementUpdate,
    QualityMetricInput,
    QualityStandardCreate,
    QualityStandardUpdate,
)


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return Session(engine)


def test_quality_measurement_and_standard_crud() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F1", name="一号工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M1", name="车型一"), db)
    color = create_color(ColorCreate(code="C1", name="珍珠白", color_type="BASECOAT"), db)
    part = create_part(PartCreate(code="P1", name="车顶"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT1",
            name="测量点一",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    group = create_measurement_group(
        MeasurementGroupCreate(
            code="G1",
            name="橘皮编组",
            vehicle_model_id=vehicle.id,
            quality_type="ORANGE_PEEL",
        ),
        db,
    )
    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-1",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    instrument = MeasurementInstrument(
        code="BYK-WAVE-1",
        name="BYK wave-scan",
        manufacturer="BYK-Gardner",
        model="wave-scan",
        instrument_type="BYK_ORANGE_PEEL",
        serial_no="BYK-WAVE-SN-1",
        supported_quality_types=["ORANGE_PEEL"],
    )
    method = MeasurementMethod(
        code="BYK-WAVE-DOI",
        name="橘皮 DOI 测量",
        version="1",
        quality_type="ORANGE_PEEL",
        instrument_type="BYK_ORANGE_PEEL",
        method_type="WAVE_SCAN",
        requires_reference=True,
        requires_direction=True,
        minimum_repeats=1,
    )
    reference = MeasurementReferenceStandard(
        code="REF-OP-1",
        name="橘皮参考件",
        quality_type="ORANGE_PEEL",
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
    )
    db.add_all([instrument, method, reference])
    db.flush()
    calibration = MeasurementCalibrationRecord(
        calibration_no="CAL-OP-1",
        instrument_id=instrument.id,
        method_id=method.id,
        reference_standard_id=reference.id,
        calibrated_at=now - timedelta(hours=1),
        valid_until=now + timedelta(hours=1),
        result="PASS",
        performed_by="质量工程师",
    )
    db.add(calibration)
    db.commit()
    standard = create_quality_standard(
        QualityStandardCreate(
            standard_no="STD-1",
            version="1",
            quality_type="ORANGE_PEEL",
            metric_code="doi",
            measurement_point_id=point.id,
            min_value=80,
            max_value=95,
        ),
        db,
    )
    assert update_quality_standard(
        standard.id,
        QualityStandardUpdate(min_value=82),
        db,
    ).min_value == 82
    assert get_quality_standard(standard.id, db).standard_no == "STD-1"

    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-1",
            production_run_id=run.id,
            measurement_group_id=group.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            instrument_id=instrument.id,
            measurement_method_id=method.id,
            calibration_record_id=calibration.id,
            reference_standard_id=reference.id,
            measurement_direction="LONGITUDINAL",
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=81)],
            repeat_readings=[
                MeasurementRepeatInput(repeat_no=1, metric_code="doi", raw_value=81)
            ],
        ),
        db,
    )
    assert measurement["judgement"] == "FAIL"
    updated = update_quality_measurement(
        measurement["id"],
        QualityMeasurementUpdate(
            measured_by="质量工程师",
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=88)],
        ),
        db,
    )
    assert updated["judgement"] == "PASS"
    assert updated["measured_by"] == "质量工程师"
    assert get_quality_measurement(measurement["id"], db)["metrics"][0].raw_value == 88
    analytics = quality_analytics(
        quality_type="ORANGE_PEEL",
        metric_code="doi",
        measurement_point_id=point.id,
        limit=500,
        db=db,
    )
    assert analytics["statistics"]["samples"] == 1
    assert analytics["statistics"]["mean"] == 88
    assert analytics["statistics"]["pass_rate"] == 1
    assert analytics["data_quality"]["standard_coverage"] == 1
    assert analytics["point_risks"][0]["risk_score"] == 0

    delete_quality_measurement(measurement["id"], db)
    delete_quality_standard(standard.id, db)
    db.close()


def test_quality_standard_rejects_invalid_range() -> None:
    db = build_session()
    with pytest.raises(HTTPException) as error:
        create_quality_standard(
            QualityStandardCreate(
                standard_no="STD-BAD",
                version="1",
                quality_type="ORANGE_PEEL",
                metric_code="doi",
                min_value=90,
                max_value=80,
            ),
            db,
        )
    assert error.value.status_code == 422
    db.close()
