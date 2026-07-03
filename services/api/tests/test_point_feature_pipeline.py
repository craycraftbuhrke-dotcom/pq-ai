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
    factory = create_factory(FactoryCreate(code="M9", name="M9 工厂"), db)
    vehicle_model = create_vehicle_model(VehicleModelCreate(code="MX11", name="MX11"), db)
    color = create_color(
        ColorCreate(code="C-01", name="珍珠白", color_type="BASECOAT", supplier="供应商 A"),
        db,
    )
    part = create_part(PartCreate(code="ROOF", name="车顶", material="钢"), db)
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle_model.id), db
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle_model.id, color_id=color.id), db
    )
    point = create_measurement_point(
        MeasurementPointCreate(
            code="P-ROOF-03",
            name="车顶中部 03",
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
            batch_no="CC-20260610-01",
            material_code="CC-01",
            material_name="清漆",
            material_type="CLEARCOAT",
            viscosity=22.5,
            solid_ratio=0.48,
            coa_values={"density": 1.03},
        ),
        db,
    )
    production_run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-001",
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
            data_no="QM-001",
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
    assert result["feature_values"]["clearcoat_2.clearcoat_2_outer_air"] == 410.0
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
