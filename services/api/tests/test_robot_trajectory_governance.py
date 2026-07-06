from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.factories import create_factory
from app.api.routes.features import build_point_snapshot
from app.api.routes.master_data import (
    create_color,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.api.routes.process import (
    create_actual_parameter,
    create_brush,
    create_brush_parameter,
    create_production_run,
    create_production_stage_run,
    create_program_version,
    create_spray_program,
)
from app.api.routes.robot_governance import (
    create_atomizer,
    create_contribution_entry,
    create_contribution_version,
    create_controller,
    create_device_configuration,
    create_device_execution,
    create_path_segment,
    create_path_segment_execution,
    create_robot,
    create_trajectory_program,
    robot_governance_summary,
    update_device_execution,
)
from tests.schema_guard import create_transient_test_schema
from app.schemas.common import FactoryCreate
from app.schemas.features import PointFeatureBuildRequest
from app.schemas.master_data import (
    ColorCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelCreate,
)
from app.schemas.process import (
    ActualParameterCreate,
    BrushCreate,
    BrushParameterCreate,
    DurrAtomizerCreate,
    DurrControllerCreate,
    DurrRobotCreate,
    PathSegmentExecutionCreate,
    PointContributionEntryCreate,
    PointContributionVersionCreate,
    ProductionDeviceExecutionCreate,
    ProductionDeviceExecutionUpdate,
    ProductionRunCreate,
    ProductionStageRunCreate,
    ProgramDeviceConfigurationCreate,
    SprayProgramCreate,
    SprayProgramVersionCreate,
    TrajectoryPathSegmentCreate,
    TrajectoryProgramCreate,
)


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def test_durr_trajectory_lineage_and_target_family_contribution_gate() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F-DURR", name="Dürr 治理工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M-DURR", name="轨迹车型"), db)
    color = create_color(
        ColorCreate(code="C-DURR", name="轨迹颜色", color_type="BASECOAT"), db
    )
    part = create_part(PartCreate(code="ROOF-DURR", name="车顶"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT-DURR",
            name="轨迹点位",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL", "THICKNESS"],
        ),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-DURR",
            name="清漆二站",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="P1C1A2",
            station_name="清漆二站",
        ),
        db,
    )
    version = create_program_version(
        program.id, SprayProgramVersionCreate(version="V1", status="ACTIVE"), db
    )
    brush = create_brush(
        version.id,
        BrushCreate(brush_no="B-DURR", brush_table_no="BT-DURR", part_id=part.id),
        db,
    )
    create_brush_parameter(
        brush.id,
        BrushParameterCreate(
            parameter_code="clearcoat_2_spray_flow",
            parameter_name="清漆二站喷涂流量",
            configured_value=300,
            unit="ml/min",
        ),
        db,
    )
    controller = create_controller(
        DurrControllerCreate(
            factory_id=factory.id,
            code="CTRL-DURR",
            name="应用控制器",
            model="受控型号",
            serial_no="CTRL-SN-DURR",
        ),
        db,
    )
    robot = create_robot(
        DurrRobotCreate(
            factory_id=factory.id,
            code="ROBOT-DURR",
            name="喷涂机器人",
            model="受控型号",
            serial_no="ROBOT-SN-DURR",
        ),
        db,
    )
    atomizer = create_atomizer(
        DurrAtomizerCreate(
            factory_id=factory.id,
            controller_id=controller.id,
            code="BELL-DURR",
            name="静电旋杯",
            model="受控型号",
            serial_no="BELL-SN-DURR",
            bell_cup_code="CUP-DURR",
        ),
        db,
    )
    configuration = create_device_configuration(
        ProgramDeviceConfigurationCreate(
            program_version_id=version.id,
            robot_id=robot.id,
            atomizer_id=atomizer.id,
            controller_id=controller.id,
            configuration_version="1.0",
            status="ACTIVE",
            approved_by="工艺工程师",
        ),
        db,
    )
    trajectory = create_trajectory_program(
        TrajectoryProgramCreate(
            program_version_id=version.id,
            trajectory_code="TRJ-DURR",
            name="车顶轨迹",
            version="1.0",
            checksum="checksum-approved",
            tcp_name="BELL-TCP",
            status="ACTIVE",
            approved_by="机器人程序员",
        ),
        db,
    )
    segment = create_path_segment(
        TrajectoryPathSegmentCreate(
            trajectory_program_id=trajectory.id,
            segment_no=1,
            name="车顶路径段",
            brush_id=brush.id,
            part_id=part.id,
            tcp_name="BELL-TCP",
            configured_speed=800,
            speed_unit="mm/s",
            trigger_state="ON",
        ),
        db,
    )
    contribution = create_contribution_version(
        PointContributionVersionCreate(
            program_version_id=version.id,
            target_family="ORANGE_PEEL",
            version="1.0",
            method="GEOMETRY",
            status="ACTIVE",
            approved_by="工艺工程师",
        ),
        db,
    )
    create_contribution_entry(
        PointContributionEntryCreate(
            contribution_version_id=contribution.id,
            measurement_point_id=point.id,
            path_segment_id=segment.id,
            overlap_ratio=0.7,
            contribution_weight=1.0,
            validation_score=0.9,
        ),
        db,
    )
    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-DURR",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    stage = create_production_stage_run(
        run.id,
        ProductionStageRunCreate(
            process_stage="CLEARCOAT_2",
            program_version_id=version.id,
        ),
        db,
    )
    create_actual_parameter(
        stage.id,
        ActualParameterCreate(
            brush_id=brush.id,
            parameter_code="clearcoat_2_spray_flow",
            actual_value=320,
            unit="ml/min",
            sampled_at=now,
            source_system="ROBOT",
        ),
        db,
    )
    execution = create_device_execution(
        ProductionDeviceExecutionCreate(
            production_stage_run_id=stage.id,
            device_configuration_id=configuration.id,
            trajectory_program_id=trajectory.id,
            executed_checksum=trajectory.checksum,
            started_at=now,
        ),
        db,
    )
    create_path_segment_execution(
        execution.id,
        PathSegmentExecutionCreate(
            path_segment_id=segment.id,
            actual_speed=820,
            speed_unit="mm/s",
            trigger_state="ON",
        ),
        db,
    )

    result = build_point_snapshot(
        PointFeatureBuildRequest(
            production_run_id=run.id,
            measurement_point_id=point.id,
            target_family="ORANGE_PEEL",
        ),
        db,
    )
    assert result["feature_values"]["clearcoat_2.spray_flow"] == 320
    assert result["feature_values"]["clearcoat_2.trajectory_path_speed"] == 820
    assert result["contribution_count"] == 1
    assert result["lineage"]["legacy_contribution_fallback"] is False
    assert result["lineage"]["contribution_version_ids"] == [contribution.id]
    assert execution.id in result["lineage"]["device_execution_ids"]
    assert trajectory.id in result["lineage"]["trajectory_program_ids"]
    summary = robot_governance_summary(db)
    assert summary["robots"] == 1
    assert summary["active_contribution_versions"] == 1
    assert summary["checksum_mismatches"] == 0

    update_device_execution(
        execution.id,
        ProductionDeviceExecutionUpdate(executed_checksum="checksum-mismatch"),
        db,
    )
    with pytest.raises(HTTPException, match="实际轨迹校验和"):
        build_point_snapshot(
            PointFeatureBuildRequest(
                production_run_id=run.id,
                measurement_point_id=point.id,
                target_family="ORANGE_PEEL",
            ),
            db,
        )
    assert robot_governance_summary(db)["checksum_mismatches"] == 1
    db.close()
