from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.factories import create_factory
from app.api.routes.features import build_point_snapshot
from app.api.routes.master_data import (
    add_measurement_group_point,
    bind_factory_vehicle_model,
    bind_vehicle_model_color,
    create_color,
    create_measurement_group,
    create_measurement_point,
    create_part,
    create_vehicle_model,
    master_data_summary,
)
from app.api.routes.process import (
    create_actual_parameter,
    create_brush,
    create_brush_parameter,
    create_material_batch,
    create_production_run,
    create_production_stage_run,
    create_program_version,
    create_spray_program,
    upsert_brush_point_contribution,
)
from app.api.routes.quality import create_quality_measurement, quality_summary
from tests.schema_guard import create_transient_test_schema
from app.models import domain  # noqa: F401
from app.models.domain import PointFeatureSnapshot, QualityMeasurement
from app.schemas.common import FactoryCreate
from app.schemas.features import PointFeatureBuildRequest
from app.schemas.master_data import (
    ColorCreate,
    FactoryVehicleModelCreate,
    MeasurementGroupCreate,
    MeasurementGroupPointCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelColorCreate,
    VehicleModelCreate,
)
from app.schemas.process import (
    ActualParameterCreate,
    BrushCreate,
    BrushParameterCreate,
    BrushPointContributionUpsert,
    MaterialBatchCreate,
    ProductionRunCreate,
    ProductionStageRunCreate,
    SprayProgramCreate,
    SprayProgramVersionCreate,
)
from app.schemas.quality import QualityMeasurementCreate, QualityMetricInput


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_transient_test_schema(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session


def test_point_feature_pipeline_aggregates_process_material_and_quality(db: Session) -> None:
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="TEST-FACTORY", name="TEST_FACTORY"), db)
    vehicle_model = create_vehicle_model(VehicleModelCreate(code="TEST-MODEL", name="TEST_MODEL"), db)
    color = create_color(
        ColorCreate(code="TEST-COLOR", name="TEST_COLOR", color_type="BASECOAT", supplier="TEST_SUPPLIER"),
        db,
    )
    part = create_part(PartCreate(code="TEST-PART", name="TEST_PART", material="TEST_MATERIAL"), db)
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle_model.id), db
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle_model.id, color_id=color.id), db
    )
    point = create_measurement_point(
        MeasurementPointCreate(
            code="TEST-POINT",
            name="TEST_POINT",
            vehicle_model_id=vehicle_model.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    group = create_measurement_group(
        MeasurementGroupCreate(
            code="G-OP-01",
            name="橘皮测量编组",
            vehicle_model_id=vehicle_model.id,
            quality_type="ORANGE_PEEL",
            expected_point_count=1,
        ),
        db,
    )
    add_measurement_group_point(
        group.id, MeasurementGroupPointCreate(measurement_point_id=point.id, sequence_no=1), db
    )

    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-C2",
            name="清漆二站",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="P1C1A2",
            station_name="清漆二站",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(
            version="V1",
            status="ACTIVE",
            vehicle_model_ids=[vehicle_model.id],
            color_ids=[color.id],
        ),
        db,
    )
    brush_1 = create_brush(
        version.id,
        BrushCreate(
            brush_no="B-041", brush_table_no="BT-C2", spray_position="车顶前部", part_id=part.id
        ),
        db,
    )
    brush_2 = create_brush(
        version.id,
        BrushCreate(
            brush_no="B-042", brush_table_no="BT-C2", spray_position="车顶后部", part_id=part.id
        ),
        db,
    )
    for brush, flow in ((brush_1, 300.0), (brush_2, 400.0)):
        create_brush_parameter(
            brush.id,
            BrushParameterCreate(
                parameter_code="spray_flow",
                parameter_name="喷涂流量",
                configured_value=flow,
                unit="ml/min",
            ),
            db,
        )
    upsert_brush_point_contribution(
        brush_1.id,
        point.id,
        BrushPointContributionUpsert(
            overlap_ratio=0.6, contribution_weight=0.6, is_approved=True
        ),
        db,
    )
    upsert_brush_point_contribution(
        brush_2.id,
        point.id,
        BrushPointContributionUpsert(
            overlap_ratio=0.4, contribution_weight=0.4, is_approved=True
        ),
        db,
    )

    material = create_material_batch(
        MaterialBatchCreate(
            batch_no="TEST-BATCH",
            material_code="TEST-MATERIAL-CODE",
            material_name="TEST_MATERIAL_NAME",
            material_type="CLEARCOAT",
            viscosity=22.5,
            solid_ratio=0.48,
            coa_values={"density": 1.03},
        ),
        db,
    )
    production_run = create_production_run(
        ProductionRunCreate(
            run_no="TEST-RUN",
            factory_id=factory.id,
            vehicle_model_id=vehicle_model.id,
            color_id=color.id,
            shift="白班",
            started_at=now,
            context_values={"batch_sequence": 12},
        ),
        db,
    )
    stage_run = create_production_stage_run(
        production_run.id,
        ProductionStageRunCreate(
            process_stage="CLEARCOAT_2",
            program_version_id=version.id,
            material_batch_id=material.id,
            actual_parameters={"clearcoat_2_outer_air": 410.0},
        ),
        db,
    )
    create_actual_parameter(
        stage_run.id,
        ActualParameterCreate(
            brush_id=brush_1.id,
            parameter_code="spray_flow",
            actual_value=320.0,
            unit="ml/min",
            sampled_at=now,
            source_system="ROBOT",
        ),
        db,
    )
    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="TEST-MEASUREMENT",
            production_run_id=production_run.id,
            measurement_group_id=group.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            metrics=[
                QualityMetricInput(
                    metric_code="doi", metric_name="DOI", raw_value=80.0, corrected_value=80.5
                )
            ],
        ),
        db,
    )
    db.get(QualityMeasurement, measurement["id"]).reliability_status = "VERIFIED"
    db.commit()
    # Simulate legacy persisted fields that predate the approved scope policy.
    production_run.context_values = {"booth_humidity": 62.0}
    stage_run.actual_parameters = {
        "booth_temperature": 24.5,
        "clearcoat_2_outer_air": 410.0,
    }
    db.commit()

    result = build_point_snapshot(
        PointFeatureBuildRequest(
            production_run_id=production_run.id, measurement_point_id=point.id
        ),
        db,
    )

    assert result["feature_values"]["clearcoat_2.spray_flow"] == pytest.approx(352.0)
    assert "clearcoat_2.material_viscosity" not in result["feature_values"]
    assert "clearcoat_2.material_solid_ratio" not in result["feature_values"]
    assert "clearcoat_2.coa.density" not in result["feature_values"]
    assert result["feature_values"]["clearcoat_2.outer_air"] == 410.0
    assert "clearcoat_2.booth_temperature" not in result["feature_values"]
    assert "context.booth_humidity" not in result["feature_values"]
    assert result["quality_labels"]["doi"] == 80.5
    assert result["contribution_count"] == 2
    assert result["stage_coverage"] == ["CLEARCOAT_2"]
    assert result["completeness_score"] == 0.2
    assert result["feature_set_version"] == "point-features-v4-material-governed"
    assert result["target_family"] == "ORANGE_PEEL"
    assert result["lineage"]["legacy_contribution_fallback"] is True

    second_result = build_point_snapshot(
        PointFeatureBuildRequest(
            production_run_id=production_run.id, measurement_point_id=point.id
        ),
        db,
    )
    assert second_result["snapshot_id"] == result["snapshot_id"]
    assert db.scalar(select(func.count()).select_from(PointFeatureSnapshot)) == 1

    master_summary = master_data_summary(db)
    assert master_summary["approved_point_contributions"] == 2
    summary = quality_summary(db)
    assert summary["measurements"] == 1
    assert summary["metric_values"] == 1


def test_point_feature_pipeline_links_five_3c3b_stages_to_one_measurement_point(
    db: Session,
) -> None:
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="FIVE", name="五工段工厂"), db)
    vehicle_model = create_vehicle_model(VehicleModelCreate(code="M3C3B", name="3C3B 车型"), db)
    color = create_color(ColorCreate(code="R-01", name="红色", color_type="BASECOAT"), db)
    part = create_part(PartCreate(code="FENDER", name="翼子板", material="钢"), db)
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle_model.id), db
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle_model.id, color_id=color.id), db
    )
    point = create_measurement_point(
        MeasurementPointCreate(
            code="P-FENDER-01",
            name="翼子板点位 01",
            vehicle_model_id=vehicle_model.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL", "COLOR_DIFFERENCE", "THICKNESS"],
        ),
        db,
    )
    group = create_measurement_group(
        MeasurementGroupCreate(
            code="G-FIVE-01",
            name="五工段点位编组",
            vehicle_model_id=vehicle_model.id,
            quality_type="ORANGE_PEEL",
            expected_point_count=1,
        ),
        db,
    )
    add_measurement_group_point(
        group.id, MeasurementGroupPointCreate(measurement_point_id=point.id, sequence_no=1), db
    )

    production_run = create_production_run(
        ProductionRunCreate(
            run_no="TEST-RUN-FIVE",
            body_no="TEST-BODY",
            factory_id=factory.id,
            vehicle_model_id=vehicle_model.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    stage_specs = [
        ("MIDCOAT_EXT", "midcoat_spray_flow", 100.0, "中涂外喷"),
        ("BASECOAT_1", "basecoat_1_spray_flow", 210.0, "色漆一站"),
        ("BASECOAT_2", "basecoat_2_spray_flow", 230.0, "色漆二站"),
        ("CLEARCOAT_1", "clearcoat_1_spray_flow", 310.0, "清漆一站"),
        ("CLEARCOAT_2", "clearcoat_2_spray_flow", 330.0, "清漆二站"),
    ]
    for index, (stage, parameter_code, configured_value, stage_name) in enumerate(
        stage_specs,
        start=1,
    ):
        program = create_spray_program(
            SprayProgramCreate(
                program_code=f"PRG-FIVE-{index}",
                name=stage_name,
                factory_id=factory.id,
                process_stage=stage,
                station_code=f"ST-{index}",
                station_name=stage_name,
            ),
            db,
        )
        version = create_program_version(
            program.id,
            SprayProgramVersionCreate(
                version="V1",
                status="ACTIVE",
                vehicle_model_ids=[vehicle_model.id],
                color_ids=[color.id],
            ),
            db,
        )
        brush = create_brush(
            version.id,
            BrushCreate(
                brush_no=f"B-{index:03d}",
                brush_table_no=f"BT-{index:03d}",
                spray_position=stage_name,
                part_id=part.id,
            ),
            db,
        )
        create_brush_parameter(
            brush.id,
            BrushParameterCreate(
                parameter_code=parameter_code,
                parameter_name="喷涂流量",
                configured_value=configured_value,
                unit="ml/min",
            ),
            db,
        )
        upsert_brush_point_contribution(
            brush.id,
            point.id,
            BrushPointContributionUpsert(
                overlap_ratio=1.0,
                contribution_weight=1.0,
                is_approved=True,
            ),
            db,
        )
        create_production_stage_run(
            production_run.id,
            ProductionStageRunCreate(
                process_stage=stage,
                program_version_id=version.id,
            ),
            db,
        )

    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-FIVE-001",
            production_run_id=production_run.id,
            measurement_group_id=group.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now,
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=82.0)],
        ),
        db,
    )
    db.get(QualityMeasurement, measurement["id"]).reliability_status = "VERIFIED"
    db.commit()

    result = build_point_snapshot(
        PointFeatureBuildRequest(
            production_run_id=production_run.id,
            measurement_point_id=point.id,
        ),
        db,
    )

    assert result["completeness_score"] == 1.0
    assert set(result["stage_coverage"]) == {stage for stage, *_ in stage_specs}
    assert result["quality_labels"]["doi"] == 82.0
    assert result["feature_values"]["midcoat.spray_flow"] == 100.0
    assert result["feature_values"]["basecoat_1.spray_flow"] == 210.0
    assert result["feature_values"]["basecoat_2.spray_flow"] == 230.0
    assert result["feature_values"]["clearcoat_1.spray_flow"] == 310.0
    assert result["feature_values"]["clearcoat_2.spray_flow"] == 330.0
    assert "midcoat.midcoat_spray_flow" not in result["feature_values"]
    assert "clearcoat_2.clearcoat_2_spray_flow" not in result["feature_values"]
