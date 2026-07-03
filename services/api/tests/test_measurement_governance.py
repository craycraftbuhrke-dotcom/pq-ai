from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.factories import create_factory
from app.api.routes.master_data import (
    create_color,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.api.routes.measurement_governance import (
    create_calibration,
    create_import_profile,
    create_instrument,
    create_method,
    create_reference,
    measurement_governance_summary,
    update_calibration,
)
from app.api.routes.process import create_production_run
from app.api.routes.quality import create_quality_measurement, get_quality_measurement
from tests.schema_guard import create_transient_test_schema
from app.models.domain import (
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementRepeatReading,
    QualityMeasurement,
    QualityMetricValue,
)
from app.schemas.common import FactoryCreate
from app.schemas.master_data import (
    ColorCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelCreate,
)
from app.schemas.process import ProductionRunCreate
from app.schemas.quality import (
    MeasurementCalibrationCreate,
    MeasurementCalibrationUpdate,
    MeasurementImportProfileCreate,
    MeasurementInstrumentCreate,
    MeasurementMethodCreate,
    MeasurementReferenceStandardCreate,
    MeasurementRepeatInput,
    QualityMeasurementCreate,
    QualityMetricInput,
)
from app.services.measurement_reliability import refresh_measurement_reliability


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def test_measurement_reliability_gate_tracks_governed_provenance() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F-GATE", name="可靠性工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M-GATE", name="可靠性车型"), db)
    color = create_color(
        ColorCreate(code="C-GATE", name="可靠性颜色", color_type="BASECOAT"),
        db,
    )
    part = create_part(PartCreate(code="P-GATE", name="车顶"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT-GATE",
            name="车顶点位",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-GATE",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )

    instrument = create_instrument(
        MeasurementInstrumentCreate(
            code="BYK-WAVE-GATE",
            name="BYK wave-scan",
            manufacturer="BYK-Gardner",
            model="wave-scan",
            instrument_type="BYK_ORANGE_PEEL",
            serial_no="SN-GATE-001",
            firmware_version="1.0",
            supported_quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    method = create_method(
        MeasurementMethodCreate(
            code="BYK-WAVE-METHOD",
            name="橘皮结构测量",
            version="1.0",
            quality_type="ORANGE_PEEL",
            instrument_type="BYK_ORANGE_PEEL",
            method_type="WAVE_SCAN",
            requires_reference=True,
            requires_direction=True,
            minimum_repeats=2,
        ),
        db,
    )
    reference = create_reference(
        MeasurementReferenceStandardCreate(
            code="REF-GATE",
            name="橘皮参考件",
            quality_type="ORANGE_PEEL",
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
        ),
        db,
    )
    profile = create_import_profile(
        MeasurementImportProfileCreate(
            code="PROFILE-GATE",
            name="BYK 导入模板",
            version="1.0",
            instrument_type="BYK_ORANGE_PEEL",
            quality_type="ORANGE_PEEL",
            schema_version="1.0",
            field_mapping={"DOI": "doi"},
        ),
        db,
    )
    calibration = create_calibration(
        MeasurementCalibrationCreate(
            calibration_no="CAL-GATE",
            instrument_id=instrument.id,
            method_id=method.id,
            reference_standard_id=reference.id,
            calibrated_at=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=1),
            result="PASS",
            performed_by="质量工程师",
        ),
        db,
    )

    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-GATE",
            production_run_id=run.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            instrument_id=instrument.id,
            measurement_method_id=method.id,
            calibration_record_id=calibration.id,
            reference_standard_id=reference.id,
            import_profile_id=profile.id,
            measurement_direction="LONGITUDINAL",
            raw_file_uri="s3://quality/QM-GATE.csv",
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=82.0)],
            repeat_readings=[
                MeasurementRepeatInput(repeat_no=1, metric_code="doi", raw_value=81.8),
                MeasurementRepeatInput(repeat_no=2, metric_code="doi", raw_value=82.2),
            ],
        ),
        db,
    )
    assert measurement["reliability_status"] == "VERIFIED"
    assert measurement["reliability_issues"] == []
    assert len(measurement["repeat_readings"]) == 2
    assert measurement_governance_summary(db)["valid_calibrations"] == 1

    update_calibration(
        calibration.id,
        MeasurementCalibrationUpdate(result="FAIL"),
        db,
    )
    failed = get_quality_measurement(measurement["id"], db)
    assert failed["reliability_status"] == "FAILED"
    assert failed["judgement"] == "INVALID"
    assert "校准/检查结果为 FAIL" in failed["reliability_issues"]
    db.close()


def test_measurement_without_provenance_is_preserved_but_unverified() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F-LEGACY", name="历史工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M-LEGACY", name="历史车型"), db)
    color = create_color(
        ColorCreate(code="C-LEGACY", name="历史颜色", color_type="BASECOAT"),
        db,
    )
    part = create_part(PartCreate(code="P-LEGACY", name="车顶"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT-LEGACY",
            name="历史点位",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-LEGACY",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-LEGACY",
            production_run_id=run.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=80.0)],
        ),
        db,
    )
    assert measurement["reliability_status"] == "UNVERIFIED"
    assert measurement["judgement"] == "INVALID"
    assert "缺少受治理测量仪器" in measurement["reliability_issues"]
    db.close()


def test_reliability_gate_enforces_layer_method_and_effect_field_profile() -> None:
    db = build_session()
    now = datetime.now(UTC)
    thickness_instrument = MeasurementInstrument(
        code="FISCHER-LAYER-GATE",
        name="Fischer 膜厚仪",
        manufacturer="Helmut Fischer",
        model="Dualscope",
        instrument_type="FISCHER_THICKNESS",
        serial_no="FISCHER-LAYER-SN",
        supported_quality_types=["THICKNESS"],
        calibration_required=False,
    )
    thickness_method = MeasurementMethod(
        code="FISCHER-TOTAL-GATE",
        name="总膜厚方法",
        version="1.0",
        quality_type="THICKNESS",
        instrument_type="FISCHER_THICKNESS",
        method_type="MAGNETIC_INDUCTION",
        layer_scope="TOTAL_FILM",
        minimum_repeats=1,
    )
    color_instrument = MeasurementInstrument(
        code="BYK-EFFECT-GATE",
        name="BYK 色差仪",
        manufacturer="BYK-Gardner",
        model="BYK-mac i",
        instrument_type="BYK_COLOR",
        serial_no="BYK-EFFECT-SN",
        supported_quality_types=["COLOR_DIFFERENCE"],
        calibration_required=False,
    )
    color_method = MeasurementMethod(
        code="BYK-EFFECT-METHOD",
        name="效应测量方法",
        version="1.0",
        quality_type="COLOR_DIFFERENCE",
        instrument_type="BYK_COLOR",
        method_type="MULTI_ANGLE_COLOR",
        minimum_repeats=1,
    )
    db.add_all([thickness_instrument, thickness_method, color_instrument, color_method])
    db.flush()

    thickness = QualityMeasurement(
        data_no="QM-LAYER-GATE",
        production_run_id="run-layer",
        measurement_point_id="point-layer",
        quality_type="THICKNESS",
        data_type="TEST",
        measured_at=now,
        instrument_id=thickness_instrument.id,
        measurement_method_id=thickness_method.id,
    )
    color = QualityMeasurement(
        data_no="QM-EFFECT-GATE",
        production_run_id="run-effect",
        measurement_point_id="point-effect",
        quality_type="COLOR_DIFFERENCE",
        data_type="TEST",
        measured_at=now,
        instrument_id=color_instrument.id,
        measurement_method_id=color_method.id,
    )
    db.add_all([thickness, color])
    db.flush()
    db.add_all(
        [
            QualityMetricValue(
                measurement_id=thickness.id,
                metric_code="thickness_midcoat",
                metric_name="中涂膜厚",
                raw_value=30.0,
            ),
            MeasurementRepeatReading(
                measurement_id=thickness.id,
                repeat_no=1,
                metric_code="thickness_midcoat",
                raw_value=30.0,
            ),
            QualityMetricValue(
                measurement_id=color.id,
                metric_code="ds15",
                metric_name="效应差异 15°",
                raw_value=0.2,
            ),
            MeasurementRepeatReading(
                measurement_id=color.id,
                repeat_no=1,
                metric_code="ds15",
                raw_value=0.2,
            ),
        ]
    )
    db.flush()

    thickness_status, thickness_issues = refresh_measurement_reliability(db, thickness)
    color_status, color_issues = refresh_measurement_reliability(db, color)
    assert thickness_status == "FAILED"
    assert "单层/单遍膜厚必须关联明确记录该层测量或推断方法的 layer_scope" in thickness_issues
    assert color_status == "UNVERIFIED"
    assert "色差效应指标必须关联版本化导入模板以确认字段语义" in color_issues
    db.close()
