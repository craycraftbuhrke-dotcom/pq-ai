from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
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
from app.api.routes.process import (
    create_brush,
    create_brush_parameter,
    create_actual_parameter,
    create_material_batch,
    create_parameter_constraint_source,
    create_parameter_definition,
    create_production_run,
    create_production_stage_run,
    create_program_version,
    create_spray_program,
    delete_brush,
    delete_brush_contribution,
    delete_brush_parameter,
    delete_actual_parameter,
    delete_material_batch,
    delete_production_run,
    delete_production_stage_run,
    delete_program_version,
    delete_spray_program,
    get_brush,
    get_brush_parameter,
    get_actual_parameter,
    get_material_batch,
    get_parameter_constraint_source,
    get_production_run,
    get_production_stage_run,
    get_program_version,
    get_spray_program,
    list_brush_contributions,
    list_actual_parameters,
    list_parameter_constraint_sources,
    update_brush,
    update_brush_parameter,
    update_actual_parameter,
    update_material_batch,
    update_parameter_constraint_source,
    update_production_run,
    update_production_stage_run,
    update_program_version,
    update_spray_program,
    upsert_brush_point_contribution,
)
from tests.schema_guard import create_transient_test_schema
from app.schemas.common import FactoryCreate
from app.schemas.master_data import ColorCreate, MeasurementPointCreate, PartCreate, VehicleModelCreate
from app.schemas.master_data import FactoryVehicleModelCreate, VehicleModelColorCreate
from app.schemas.process import (
    BrushCreate,
    ActualParameterCreate,
    ActualParameterUpdate,
    BrushParameterCreate,
    BrushParameterUpdate,
    BrushPointContributionUpsert,
    BrushUpdate,
    MaterialBatchCreate,
    MaterialBatchUpdate,
    ParameterConstraintSourceCreate,
    ParameterConstraintSourceUpdate,
    ParameterDefinitionCreate,
    ProductionRunCreate,
    ProductionRunUpdate,
    ProductionStageRunCreate,
    ProductionStageRunUpdate,
    SprayProgramCreate,
    SprayProgramUpdate,
    SprayProgramVersionCreate,
    SprayProgramVersionUpdate,
)


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    create_transient_test_schema(engine)
    return Session(engine)


def assert_delete_disabled(callable_, *args) -> None:
    with pytest.raises(HTTPException) as error:
        callable_(*args)
    assert error.value.status_code == 405


def test_program_version_brush_parameter_and_contribution_crud() -> None:
    db = build_session()
    factory = create_factory(FactoryCreate(code="F01", name="TEST_FACTORY_ONE"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M01", name="TEST_MODEL_ONE"), db)
    color = create_color(ColorCreate(code="C01", name="TEST_COLOR_ONE", color_type="BASECOAT"), db)
    part = create_part(PartCreate(code="ROOF", name="TEST_PART_ONE"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="P01",
            name="TEST_POINT_ONE",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-01",
            name="清漆二站",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="P1C1A2",
            station_name="清漆二站",
        ),
        db,
    )
    assert update_spray_program(
        program.id,
        SprayProgramUpdate(robot_model="Robot-X"),
        db,
    ).robot_model == "Robot-X"
    assert get_spray_program(program.id, db).program_code == "PRG-01"

    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(
            version="V1",
            vehicle_model_ids=[vehicle.id],
            color_ids=[color.id],
        ),
        db,
    )
    activated = update_program_version(
        version.id,
        SprayProgramVersionUpdate(status="ACTIVE", approved_by="审批人"),
        db,
    )
    assert activated.status == "ACTIVE"
    assert activated.approved_at is not None
    assert activated.effective_from is not None
    assert get_program_version(version.id, db).version == "V1"

    brush = create_brush(
        version.id,
        BrushCreate(brush_no="B01", brush_table_no="BT01", part_id=part.id),
        db,
    )
    assert update_brush(brush.id, BrushUpdate(spray_position="车顶前部"), db).spray_position == "车顶前部"
    assert get_brush(brush.id, db).brush_no == "B01"
    parameter = create_brush_parameter(
        brush.id,
        BrushParameterCreate(
            parameter_code="clearcoat_2_spray_flow",
            parameter_name="清漆二站喷涂流量",
            configured_value=320,
            unit="ml/min",
        ),
        db,
    )
    assert update_brush_parameter(
        parameter.id,
        BrushParameterUpdate(configured_value=330),
        db,
    ).configured_value == 330
    assert get_brush_parameter(parameter.id, db).parameter_code == "clearcoat_2_spray_flow"

    upsert_brush_point_contribution(
        brush.id,
        point.id,
        BrushPointContributionUpsert(overlap_ratio=0.6, contribution_weight=0.6),
        db,
    )
    assert len(list_brush_contributions(brush.id, db)) == 1
    assert_delete_disabled(delete_brush_contribution, brush.id, point.id, db)
    assert_delete_disabled(delete_brush_parameter, parameter.id, db)
    assert_delete_disabled(delete_brush, brush.id, db)
    assert_delete_disabled(delete_program_version, version.id, db)
    assert_delete_disabled(delete_spray_program, program.id, db)
    db.close()


def test_program_with_version_cannot_be_deleted() -> None:
    db = build_session()
    factory = create_factory(FactoryCreate(code="F02", name="二号工厂"), db)
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-02",
            name="中涂外喷",
            factory_id=factory.id,
            process_stage="MIDCOAT_EXT",
            station_code="P1F1A1",
            station_name="中涂外喷",
        ),
        db,
    )
    create_program_version(program.id, SprayProgramVersionCreate(version="V1"), db)
    assert_delete_disabled(delete_spray_program, program.id, db)
    db.close()


def test_program_version_applicability_cannot_shrink_in_place() -> None:
    db = build_session()
    factory = create_factory(FactoryCreate(code="F02A", name="二号A工厂"), db)
    vehicle_a = create_vehicle_model(VehicleModelCreate(code="M02A", name="车型A"), db)
    vehicle_b = create_vehicle_model(VehicleModelCreate(code="M02B", name="车型B"), db)
    color_a = create_color(ColorCreate(code="C02A", name="颜色A", color_type="BASECOAT"), db)
    color_b = create_color(ColorCreate(code="C02B", name="颜色B", color_type="BASECOAT"), db)
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-02A",
            name="色漆一站",
            factory_id=factory.id,
            process_stage="BASECOAT_1",
            station_code="P1B1A1",
            station_name="色漆一站",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(
            version="V1",
            vehicle_model_ids=[vehicle_a.id, vehicle_b.id],
            color_ids=[color_a.id, color_b.id],
        ),
        db,
    )

    expanded = update_program_version(
        version.id,
        SprayProgramVersionUpdate(vehicle_model_ids=[vehicle_a.id, vehicle_b.id], color_ids=[color_a.id, color_b.id]),
        db,
    )
    assert expanded.id == version.id

    with pytest.raises(HTTPException) as vehicle_error:
        update_program_version(
            version.id,
            SprayProgramVersionUpdate(vehicle_model_ids=[vehicle_a.id]),
            db,
        )
    assert vehicle_error.value.status_code == 422

    with pytest.raises(HTTPException) as color_error:
        update_program_version(
            version.id,
            SprayProgramVersionUpdate(color_ids=[color_a.id]),
            db,
        )
    assert color_error.value.status_code == 422
    db.close()


def test_brush_point_contribution_requires_matching_point_context() -> None:
    db = build_session()
    factory = create_factory(FactoryCreate(code="F02B", name="二号B工厂"), db)
    vehicle_a = create_vehicle_model(VehicleModelCreate(code="M02C", name="车型C"), db)
    vehicle_b = create_vehicle_model(VehicleModelCreate(code="M02D", name="车型D"), db)
    part_roof = create_part(PartCreate(code="ROOF2", name="车顶"), db)
    part_door = create_part(PartCreate(code="DOOR2", name="车门"), db)
    quality_point = create_measurement_point(
        MeasurementPointCreate(
            code="P02A",
            name="车顶橘皮点",
            vehicle_model_id=vehicle_a.id,
            part_id=part_roof.id,
            point_type="QUALITY",
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    wrong_vehicle_point = create_measurement_point(
        MeasurementPointCreate(
            code="P02B",
            name="异车型点",
            vehicle_model_id=vehicle_b.id,
            part_id=part_roof.id,
            point_type="QUALITY",
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    wrong_part_point = create_measurement_point(
        MeasurementPointCreate(
            code="P02C",
            name="异零件点",
            vehicle_model_id=vehicle_a.id,
            part_id=part_door.id,
            point_type="QUALITY",
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    non_quality_point = create_measurement_point(
        MeasurementPointCreate(
            code="P02D",
            name="非质量点",
            vehicle_model_id=vehicle_a.id,
            part_id=part_roof.id,
            point_type="PROCESS",
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-02B",
            name="清漆一站",
            factory_id=factory.id,
            process_stage="CLEARCOAT_1",
            station_code="P1C1A1",
            station_name="清漆一站",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V1", vehicle_model_ids=[vehicle_a.id]),
        db,
    )
    brush = create_brush(
        version.id,
        BrushCreate(brush_no="B02", brush_table_no="BT02", part_id=part_roof.id),
        db,
    )

    upsert_brush_point_contribution(
        brush.id,
        quality_point.id,
        BrushPointContributionUpsert(overlap_ratio=0.5, contribution_weight=0.5),
        db,
    )

    with pytest.raises(HTTPException) as vehicle_error:
        upsert_brush_point_contribution(
            brush.id,
            wrong_vehicle_point.id,
            BrushPointContributionUpsert(overlap_ratio=0.5, contribution_weight=0.5),
            db,
        )
    assert vehicle_error.value.status_code == 422

    with pytest.raises(HTTPException) as part_error:
        upsert_brush_point_contribution(
            brush.id,
            wrong_part_point.id,
            BrushPointContributionUpsert(overlap_ratio=0.5, contribution_weight=0.5),
            db,
        )
    assert part_error.value.status_code == 422

    with pytest.raises(HTTPException) as point_type_error:
        upsert_brush_point_contribution(
            brush.id,
            non_quality_point.id,
            BrushPointContributionUpsert(overlap_ratio=0.5, contribution_weight=0.5),
            db,
        )
    assert point_type_error.value.status_code == 422
    db.close()


def test_parameter_constraint_source_crud_and_activation_gate() -> None:
    db = build_session()
    factory = create_factory(FactoryCreate(code="F03", name="三号工厂"), db)
    definition = create_parameter_definition(
        ParameterDefinitionCreate(
            code="clearcoat_2_spray_flow",
            name="清漆二站喷涂流量",
            category="CLEARCOAT_2",
            unit="ml/min",
            hard_min=250,
            hard_max=380,
            is_recommendable=True,
        ),
        db,
    )
    with pytest.raises(HTTPException) as error:
        create_parameter_constraint_source(
            ParameterConstraintSourceCreate(
                parameter_definition_id=definition.id,
                factory_id=factory.id,
                process_stage="CLEARCOAT_2",
                constraint_code="F03-CC2-FLOW-STD",
                version="1.0",
                source_type="FACTORY_PROCESS_STANDARD",
                lower_limit=280,
                upper_limit=360,
                unit="ml/min",
                status="ACTIVE",
            ),
            db,
        )
    assert error.value.status_code == 422
    source = create_parameter_constraint_source(
        ParameterConstraintSourceCreate(
            parameter_definition_id=definition.id,
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            constraint_code="F03-CC2-FLOW-STD",
            version="1.0",
            source_type="FACTORY_PROCESS_STANDARD",
            source_uri="file://factory-standard/cc2-flow",
            lower_limit=280,
            upper_limit=360,
            unit="ml/min",
            status="ACTIVE",
            approved_by="工艺负责人",
        ),
        db,
    )
    assert source.status == "ACTIVE"
    assert source.approved_at is not None
    assert get_parameter_constraint_source(source.id, db).constraint_code == "F03-CC2-FLOW-STD"
    updated = update_parameter_constraint_source(
        source.id,
        ParameterConstraintSourceUpdate(upper_limit=365, remark="DOE 后放宽上限"),
        db,
    )
    assert updated.upper_limit == 365
    assert len(list_parameter_constraint_sources(db)) == 1
    db.close()


def test_production_material_stage_and_actual_parameter_crud() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F05", name="五号工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M05", name="车型五"), db)
    color = create_color(ColorCreate(code="C05", name="蓝色", color_type="BASECOAT"), db)
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle.id),
        db,
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle.id, color_id=color.id),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-05",
            name="清漆一站",
            factory_id=factory.id,
            process_stage="CLEARCOAT_1",
            station_code="P1C1A1",
            station_name="清漆一站",
        ),
        db,
    )
    version = create_program_version(program.id, SprayProgramVersionCreate(version="V1"), db)
    batch = create_material_batch(
        MaterialBatchCreate(
            batch_no="LOT-05",
            material_code="CC-05",
            material_name="清漆",
            material_type="CLEARCOAT",
        ),
        db,
    )
    assert update_material_batch(
        batch.id,
        MaterialBatchUpdate(viscosity=24.5, solid_ratio=0.51),
        db,
    ).viscosity == 24.5
    assert get_material_batch(batch.id, db).batch_no == "LOT-05"

    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-05",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    assert update_production_run(
        run.id,
        ProductionRunUpdate(body_no="BODY-05", shift="DAY"),
        db,
    ).body_no == "BODY-05"
    assert get_production_run(run.id, db).run_no == "RUN-05"
    stage = create_production_stage_run(
        run.id,
        ProductionStageRunCreate(
            process_stage="CLEARCOAT_1",
            program_version_id=version.id,
            material_batch_id=batch.id,
        ),
        db,
    )
    assert update_production_stage_run(
        stage.id,
        ProductionStageRunUpdate(status="VERIFIED"),
        db,
    ).status == "VERIFIED"
    assert get_production_stage_run(stage.id, db).process_stage == "CLEARCOAT_1"
    actual = create_actual_parameter(
        stage.id,
        ActualParameterCreate(
            parameter_code="clearcoat_1_spray_flow",
            actual_value=310,
            unit="ml/min",
            sampled_at=now,
            source_system="PLC",
        ),
        db,
    )
    assert update_actual_parameter(
        actual.id,
        ActualParameterUpdate(actual_value=312),
        db,
    ).actual_value == 312
    assert get_actual_parameter(actual.id, db).parameter_code == "clearcoat_1_spray_flow"
    assert len(list_actual_parameters(stage.id, db)) == 1
    assert_delete_disabled(delete_actual_parameter, actual.id, db)
    assert_delete_disabled(delete_production_stage_run, stage.id, db)
    assert_delete_disabled(delete_production_run, run.id, db)
    assert_delete_disabled(delete_material_batch, batch.id, db)
    assert_delete_disabled(delete_program_version, version.id, db)
    assert_delete_disabled(delete_spray_program, program.id, db)
    db.close()


def test_production_run_requires_active_factory_model_and_model_color_mapping() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F06", name="六号工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M06", name="车型六"), db)
    color = create_color(ColorCreate(code="C06", name="银色", color_type="BASECOAT"), db)

    with pytest.raises(HTTPException) as error:
        create_production_run(
            ProductionRunCreate(
                run_no="RUN-06",
                factory_id=factory.id,
                vehicle_model_id=vehicle.id,
                color_id=color.id,
                started_at=now,
            ),
            db,
        )
    assert error.value.status_code == 422

    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle.id),
        db,
    )
    with pytest.raises(HTTPException) as color_error:
        create_production_run(
            ProductionRunCreate(
                run_no="RUN-06-B",
                factory_id=factory.id,
                vehicle_model_id=vehicle.id,
                color_id=color.id,
                started_at=now,
            ),
            db,
        )
    assert color_error.value.status_code == 422

    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle.id, color_id=color.id),
        db,
    )
    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-06-C",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    assert run.run_no == "RUN-06-C"
    db.close()


def test_stage_run_rejects_mismatched_program_or_material_context() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F07", name="七号工厂"), db)
    other_factory = create_factory(FactoryCreate(code="F08", name="八号工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M07", name="车型七"), db)
    other_vehicle = create_vehicle_model(VehicleModelCreate(code="M08", name="车型八"), db)
    color = create_color(ColorCreate(code="C07", name="黑色", color_type="BASECOAT"), db)
    other_color = create_color(ColorCreate(code="C08", name="白色", color_type="BASECOAT"), db)

    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle.id),
        db,
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle.id, color_id=color.id),
        db,
    )

    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-07",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )

    wrong_stage_program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-07-WRONG-STAGE",
            name="色漆一站",
            factory_id=factory.id,
            process_stage="BASECOAT_1",
            station_code="P1B1A1",
            station_name="色漆一站",
        ),
        db,
    )
    wrong_stage_version = create_program_version(
        wrong_stage_program.id,
        SprayProgramVersionCreate(version="V1"),
        db,
    )
    with pytest.raises(HTTPException) as stage_error:
        create_production_stage_run(
            run.id,
            ProductionStageRunCreate(
                process_stage="CLEARCOAT_1",
                program_version_id=wrong_stage_version.id,
            ),
            db,
        )
    assert stage_error.value.status_code == 422

    wrong_factory_program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-07-WRONG-FACTORY",
            name="清漆一站",
            factory_id=other_factory.id,
            process_stage="CLEARCOAT_1",
            station_code="P1C1A1",
            station_name="清漆一站",
        ),
        db,
    )
    wrong_factory_version = create_program_version(
        wrong_factory_program.id,
        SprayProgramVersionCreate(version="V1"),
        db,
    )
    with pytest.raises(HTTPException) as factory_error:
        create_production_stage_run(
            run.id,
            ProductionStageRunCreate(
                process_stage="CLEARCOAT_1",
                program_version_id=wrong_factory_version.id,
            ),
            db,
        )
    assert factory_error.value.status_code == 422

    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-07",
            name="清漆一站",
            factory_id=factory.id,
            process_stage="CLEARCOAT_1",
            station_code="P1C1A1",
            station_name="清漆一站",
        ),
        db,
    )
    constrained_version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V1", vehicle_model_ids=[other_vehicle.id]),
        db,
    )
    with pytest.raises(HTTPException) as vehicle_error:
        create_production_stage_run(
            run.id,
            ProductionStageRunCreate(
                process_stage="CLEARCOAT_1",
                program_version_id=constrained_version.id,
            ),
            db,
        )
    assert vehicle_error.value.status_code == 422

    constrained_color_version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V2", color_ids=[other_color.id]),
        db,
    )
    with pytest.raises(HTTPException) as color_error:
        create_production_stage_run(
            run.id,
            ProductionStageRunCreate(
                process_stage="CLEARCOAT_1",
                program_version_id=constrained_color_version.id,
            ),
            db,
        )
    assert color_error.value.status_code == 422

    batch = create_material_batch(
        MaterialBatchCreate(
            batch_no="LOT-07",
            material_code="BC-07",
            material_name="色漆",
            material_type="BASECOAT",
        ),
        db,
    )
    valid_version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V3"),
        db,
    )
    with pytest.raises(HTTPException) as batch_error:
        create_production_stage_run(
            run.id,
            ProductionStageRunCreate(
                process_stage="CLEARCOAT_1",
                program_version_id=valid_version.id,
                material_batch_id=batch.id,
            ),
            db,
        )
    assert batch_error.value.status_code == 422
    db.close()
