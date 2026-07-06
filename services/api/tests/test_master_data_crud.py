import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.api.routes.factories import (
    create_factory,
    delete_factory,
    get_factory,
    update_factory,
)
from app.api.routes.master_data import (
    create_color,
    create_measurement_group,
    create_measurement_point,
    create_part,
    create_vehicle_model,
    delete_color,
    delete_measurement_group,
    delete_measurement_point,
    delete_part,
    delete_vehicle_model,
    get_color,
    get_measurement_group,
    get_measurement_point,
    get_part,
    get_vehicle_model,
    update_color,
    update_measurement_group,
    update_measurement_point,
    update_part,
    update_vehicle_model,
    bind_factory_vehicle_model,
    bind_measurement_group_point,
    bind_vehicle_model_color,
    delete_factory_vehicle_model,
    delete_measurement_group_point,
    delete_vehicle_model_color,
    list_factory_vehicle_models,
    list_measurement_group_points,
    list_vehicle_model_colors,
)
from tests.schema_guard import create_transient_test_schema
from app.schemas.common import FactoryCreate, FactoryUpdate
from app.schemas.master_data import (
    ColorCreate,
    ColorUpdate,
    FactoryVehicleModelCreate,
    MeasurementGroupPointBind,
    MeasurementGroupCreate,
    MeasurementGroupUpdate,
    MeasurementPointCreate,
    MeasurementPointUpdate,
    PartCreate,
    PartUpdate,
    VehicleModelCreate,
    VehicleModelColorCreate,
    VehicleModelUpdate,
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


def test_factory_crud_and_duplicate_code_validation() -> None:
    db = build_session()
    factory = create_factory(
        FactoryCreate(code="F01", name="TEST_FACTORY_ONE", site_owner="TEST_OWNER"),
        db,
    )
    assert get_factory(factory.id, db).site_owner == "TEST_OWNER"
    updated = update_factory(factory.id, FactoryUpdate(name="TEST_FACTORY_ONE_UPDATED", is_active=False), db)
    assert updated.name == "TEST_FACTORY_ONE_UPDATED"
    assert updated.is_active is False

    create_factory(FactoryCreate(code="F02", name="TEST_FACTORY_TWO"), db)
    with pytest.raises(HTTPException) as error:
        update_factory(factory.id, FactoryUpdate(code="F02"), db)
    assert error.value.status_code == 409

    assert_delete_disabled(delete_factory, factory.id, db)
    assert get_factory(factory.id, db).id == factory.id
    db.close()


def test_vehicle_color_and_part_crud() -> None:
    db = build_session()
    vehicle = create_vehicle_model(VehicleModelCreate(code="M01", name="TEST_MODEL_ONE"), db)
    color = create_color(
        ColorCreate(
            code="C01",
            name="TEST_COLOR_ONE",
            color_type="BASECOAT",
            supplier="TEST_SUPPLIER_A",
            tds_uri="https://docs.local/tds/c01",
            digital_standard={"dE45": 0.8},
        ),
        db,
    )
    part = create_part(PartCreate(code="P01", name="TEST_PART_ONE", material="TEST_MATERIAL"), db)

    assert get_vehicle_model(vehicle.id, db).code == "M01"
    assert get_color(color.id, db).supplier == "TEST_SUPPLIER_A"
    assert get_color(color.id, db).tds_uri == "https://docs.local/tds/c01"
    assert get_part(part.id, db).material == "TEST_MATERIAL"

    assert update_vehicle_model(vehicle.id, VehicleModelUpdate(name="TEST_MODEL_ONE_UPDATED"), db).name == "TEST_MODEL_ONE_UPDATED"
    assert update_color(color.id, ColorUpdate(supplier="TEST_SUPPLIER_B"), db).supplier == "TEST_SUPPLIER_B"
    assert update_part(part.id, PartUpdate(region="TEST_REGION"), db).region == "TEST_REGION"

    assert_delete_disabled(delete_vehicle_model, vehicle.id, db)
    assert_delete_disabled(delete_color, color.id, db)
    assert_delete_disabled(delete_part, part.id, db)
    db.close()


def test_measurement_group_and_point_crud() -> None:
    db = build_session()
    vehicle = create_vehicle_model(VehicleModelCreate(code="M02", name="TEST_MODEL_TWO"), db)
    part = create_part(PartCreate(code="P02", name="TEST_PART_TWO", material="TEST_MATERIAL"), db)
    group = create_measurement_group(
        MeasurementGroupCreate(
            code="G-OP",
            name="TEST_GROUP",
            vehicle_model_id=vehicle.id,
            quality_type="ORANGE_PEEL",
            expected_point_count=1,
        ),
        db,
    )
    point = create_measurement_point(
        MeasurementPointCreate(
            code="TEST-POINT-01",
            name="TEST_POINT_ONE",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            region="TEST_REGION",
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    factory = create_factory(FactoryCreate(code="F04", name="TEST_FACTORY_FOUR"), db)
    factory_relation = bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle.id),
        db,
    )
    color = create_color(ColorCreate(code="C04", name="银色", color_type="BASECOAT"), db)
    color_relation = bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle.id, color_id=color.id),
        db,
    )
    point_relation = bind_measurement_group_point(
        MeasurementGroupPointBind(
            measurement_group_id=group.id,
            measurement_point_id=point.id,
            sequence_no=1,
        ),
        db,
    )
    assert len(list_factory_vehicle_models(db)) == 1
    assert len(list_vehicle_model_colors(db)) == 1
    assert len(list_measurement_group_points(db)) == 1

    assert get_measurement_group(group.id, db).quality_type == "ORANGE_PEEL"
    assert get_measurement_point(point.id, db).part_id == part.id
    assert (
        update_measurement_group(
            group.id,
            MeasurementGroupUpdate(expected_point_count=2),
            db,
        ).expected_point_count
        == 2
    )
    assert update_measurement_point(
        point.id,
        MeasurementPointUpdate(is_match_point=True),
        db,
    ).is_match_point

    assert_delete_disabled(delete_measurement_group_point, point_relation.id, db)
    assert_delete_disabled(delete_factory_vehicle_model, factory_relation.id, db)
    assert_delete_disabled(delete_vehicle_model_color, color_relation.id, db)
    assert_delete_disabled(delete_measurement_group, group.id, db)
    assert_delete_disabled(delete_measurement_point, point.id, db)
    assert_delete_disabled(delete_factory, factory.id, db)
    assert_delete_disabled(delete_color, color.id, db)
    db.close()


def test_referenced_factory_cannot_be_deleted() -> None:
    db = build_session()
    factory = create_factory(FactoryCreate(code="F03", name="三号工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M03", name="车型三"), db)
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle.id),
        db,
    )

    assert_delete_disabled(delete_factory, factory.id, db)
    assert get_factory(factory.id, db).id == factory.id
    db.close()
