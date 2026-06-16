from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.api.routes.factories import create_factory
from app.api.routes.master_data import create_color, create_measurement_point, create_part, create_vehicle_model
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
from app.db.base import Base
from app.schemas.common import FactoryCreate
from app.schemas.master_data import ColorCreate, MeasurementPointCreate, PartCreate, VehicleModelCreate
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

    Base.metadata.create_all(engine)
    return Session(engine)


def test_program_version_brush_parameter_and_contribution_crud() -> None:
    db = build_session()
    factory = create_factory(FactoryCreate(code="F01", name="一号工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M01", name="车型一"), db)
    color = create_color(ColorCreate(code="C01", name="珍珠白", color_type="BASECOAT"), db)
    part = create_part(PartCreate(code="ROOF", name="车顶"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="P01",
            name="点位一",
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
    delete_brush_contribution(brush.id, point.id, db)
    delete_brush_parameter(parameter.id, db)
    delete_brush(brush.id, db)
    delete_program_version(version.id, db)
    delete_spray_program(program.id, db)
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
    with pytest.raises(HTTPException) as error:
        delete_spray_program(program.id, db)
    assert error.value.status_code == 409
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
    delete_actual_parameter(actual.id, db)
    delete_production_stage_run(stage.id, db)
    delete_production_run(run.id, db)
    delete_material_batch(batch.id, db)
    delete_program_version(version.id, db)
    delete_spray_program(program.id, db)
    db.close()
