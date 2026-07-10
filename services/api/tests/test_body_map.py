from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.body_map import (
    create_body_map_point,
    deactivate_body_map_layout,
    get_body_map,
    get_body_map_point_detail,
    upsert_body_map_layout,
)
from app.api.routes.factories import create_factory
from app.api.routes.master_data import (
    create_measurement_group,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.api.routes.process import (
    create_brush,
    create_brush_parameter,
    create_program_version,
    create_spray_program,
    upsert_brush_point_contribution,
)
from app.api.routes.quality import create_quality_measurement
from app.models.domain import MeasurementPointLayout
from app.schemas.common import FactoryCreate
from app.schemas.master_data import (
    MeasurementGroupCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelCreate,
)
from app.schemas.process import (
    BrushCreate,
    BrushParameterCreate,
    BrushPointContributionUpsert,
    SprayProgramCreate,
    SprayProgramVersionCreate,
)
from app.schemas.quality import (
    BodyMapLayoutDeactivate,
    BodyMapLayoutUpsert,
    BodyMapPointCreate,
    QualityMeasurementCreate,
    QualityMetricInput,
)
from app.api.routes.process import create_production_run
from app.schemas.process import ProductionRunCreate
from app.api.routes.master_data import bind_factory_vehicle_model, bind_vehicle_model_color, create_color
from app.schemas.master_data import ColorCreate, FactoryVehicleModelCreate, VehicleModelColorCreate
from tests.schema_guard import create_transient_test_schema


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def build_body_map_context(db: Session) -> dict:
    factory = create_factory(FactoryCreate(code="F-BM", name="Body Map Factory"), db)
    model = create_vehicle_model(VehicleModelCreate(code="VM-BM", name="Body Map Model"), db)
    color = create_color(ColorCreate(code="C-BM", name="Silver", color_type="BASECOAT"), db)
    part = create_part(PartCreate(code="PART-BM", name="Door Outer"), db)
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=model.id, is_active=True),
        db,
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=model.id, color_id=color.id, is_active=True),
        db,
    )
    group = create_measurement_group(
        MeasurementGroupCreate(
            code="G-BM",
            name="Door OP Group",
            vehicle_model_id=model.id,
            quality_type="ORANGE_PEEL",
        ),
        db,
    )
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT-BM",
            name="Door Center",
            vehicle_model_id=model.id,
            part_id=part.id,
            point_type="QUALITY",
            region="Door",
            quality_types=["ORANGE_PEEL", "COLOR_DIFFERENCE", "THICKNESS"],
        ),
        db,
    )
    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-BM-1",
            body_no="BODY-BM-1",
            factory_id=factory.id,
            vehicle_model_id=model.id,
            color_id=color.id,
            started_at=datetime(2026, 7, 10, 8, 0, tzinfo=UTC),
        ),
        db,
    )
    return {
        "factory": factory,
        "model": model,
        "color": color,
        "part": part,
        "group": group,
        "point": point,
        "run": run,
    }


def test_body_map_layout_snaps_to_grid_center() -> None:
    db = build_session()
    context = build_body_map_context(db)
    point = context["point"]

    layout = upsert_body_map_layout(
        point.id,
        BodyMapLayoutUpsert(body_view="TOP", layout_x=0.21, layout_y=0.39),
        db,
    )
    assert layout.grid_col == int(0.21 * 48)
    assert layout.grid_row == int(0.39 * 24)
    assert abs(layout.layout_x - ((layout.grid_col + 0.5) / 48)) < 1e-9
    assert abs(layout.layout_y - ((layout.grid_row + 0.5) / 24)) < 1e-9

    body_map = get_body_map(vehicle_model_id=context["model"].id, body_view="TOP", db=db)
    assert body_map.placed_count == 1
    assert body_map.background_image_url == "/body-maps/top.jpg"
    db.close()


def test_body_map_layout_upsert_and_deactivate() -> None:
    db = build_session()
    context = build_body_map_context(db)
    point = context["point"]

    layout = upsert_body_map_layout(
        point.id,
        BodyMapLayoutUpsert(body_view="SIDE", layout_x=0.42, layout_y=0.55),
        db,
    )
    assert layout.status == "ACTIVE"
    assert layout.grid_col == int(0.42 * 48)
    assert layout.grid_row == int(0.55 * 24)
    assert abs(layout.layout_x - ((layout.grid_col + 0.5) / 48)) < 1e-9

    body_map = get_body_map(
        vehicle_model_id=context["model"].id,
        body_view="SIDE",
        db=db,
    )
    mapped = next(item for item in body_map.points if item.measurement_point_id == point.id)
    assert mapped.layout_x == layout.layout_x
    assert mapped.layout_y == layout.layout_y
    assert body_map.background_image_url == "/body-maps/side.jpg"
    assert body_map.placed_count == 1

    deactivated = deactivate_body_map_layout(
        layout.id,
        BodyMapLayoutDeactivate(body_view="SIDE"),
        db,
    )
    assert deactivated.status == "INACTIVE"
    assert db.get(MeasurementPointLayout, layout.id).status == "INACTIVE"

    body_map_after = get_body_map(
        vehicle_model_id=context["model"].id,
        body_view="SIDE",
        db=db,
    )
    mapped_after = next(
        item for item in body_map_after.points if item.measurement_point_id == point.id
    )
    assert mapped_after.layout_x is None
    db.close()


def test_body_map_create_point_binds_group_and_detail_includes_brush() -> None:
    db = build_session()
    context = build_body_map_context(db)
    model = context["model"]
    part = context["part"]
    group = context["group"]
    run = context["run"]

    created = create_body_map_point(
        BodyMapPointCreate(
            vehicle_model_id=model.id,
            body_view="TOP",
            layout_x=0.3,
            layout_y=0.4,
            code="PT-NEW",
            name="Hood Point",
            part_id=part.id,
            measurement_group_id=group.id,
        ),
        db,
    )
    assert created.code == "PT-NEW"
    assert created.grid_col == int(0.3 * 48)
    assert created.grid_row == int(0.4 * 24)
    assert abs(created.layout_x - ((created.grid_col + 0.5) / 48)) < 1e-9
    assert created.in_group is True

    body_map = get_body_map(
        vehicle_model_id=model.id,
        body_view="TOP",
        measurement_group_id=group.id,
        db=db,
    )
    assert any(item.measurement_point_id == created.measurement_point_id and item.in_group for item in body_map.points)

    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-BM",
            name="Clearcoat Program",
            factory_id=context["factory"].id,
            process_stage="CLEARCOAT_1",
            station_code="ST-BM",
            station_name="Station BM",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V1", vehicle_model_ids=[model.id]),
        db,
    )
    brush = create_brush(version.id, BrushCreate(brush_no="B01", brush_table_no="BT01", part_id=part.id), db)
    create_brush_parameter(
        brush.id,
        BrushParameterCreate(
            parameter_code="flow",
            parameter_name="流量",
            configured_value=280,
            unit="ml/min",
        ),
        db,
    )
    upsert_brush_point_contribution(
        brush.id,
        created.measurement_point_id,
        BrushPointContributionUpsert(overlap_ratio=0.5, contribution_weight=0.6),
        db,
    )
    create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-BM-1",
            production_run_id=run.id,
            measurement_point_id=created.measurement_point_id,
            quality_type="ORANGE_PEEL",
            measured_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=88.5)],
        ),
        db,
    )

    detail = get_body_map_point_detail(created.measurement_point_id, production_run_id=run.id, db=db)
    assert detail.code == "PT-NEW"
    orange = next(item for item in detail.quality_summaries if item.quality_type == "ORANGE_PEEL")
    assert orange.value == 88.5
    assert len(detail.brush_contributions) == 1
    assert detail.brush_contributions[0].brush_no == "B01"
    assert detail.brush_contributions[0].coating_system == "CLEARCOAT"
    assert detail.brush_contributions[0].parameters[0].configured_value == 280
    db.close()
