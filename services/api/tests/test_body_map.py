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
    bind_factory_vehicle_model,
    bind_vehicle_model_color,
    create_color,
    create_measurement_group,
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
    upsert_brush_point_contribution,
)
from app.api.routes.quality import create_quality_measurement
from app.api.routes.robot_governance import (
    create_contribution_entry,
    create_contribution_version,
)
from app.models.domain import MeasurementPointLayout, QualityMeasurement
from app.schemas.common import FactoryCreate
from app.schemas.master_data import (
    ColorCreate,
    FactoryVehicleModelCreate,
    MeasurementGroupCreate,
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
    PointContributionEntryCreate,
    PointContributionVersionCreate,
    ProductionRunCreate,
    ProductionStageRunCreate,
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
from app.services.measurement_reliability import VERIFIED
from tests.schema_guard import create_transient_test_schema


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def mark_verified(db: Session, measurement_id: str) -> QualityMeasurement:
    measurement = db.get(QualityMeasurement, measurement_id)
    assert measurement is not None
    measurement.reliability_status = VERIFIED
    measurement.reliability_issues = []
    measurement.is_valid = True
    db.commit()
    db.refresh(measurement)
    return measurement


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
    assert body_map.production_run_id == context["run"].id
    assert body_map.production_run_no == "RUN-BM-1"
    assert body_map.quality_scope == "VERIFIED"
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
    assert layout.body_view == "RIGHT"
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
    assert body_map.body_view == "RIGHT"
    assert body_map.background_image_url == "/body-maps/side.jpg"
    assert body_map.placed_count == 1

    deactivated = deactivate_body_map_layout(
        layout.id,
        BodyMapLayoutDeactivate(body_view="RIGHT"),
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
    measurement = create_quality_measurement(
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
    mark_verified(db, measurement["id"])

    detail = get_body_map_point_detail(created.measurement_point_id, production_run_id=run.id, db=db)
    assert detail.code == "PT-NEW"
    orange = next(item for item in detail.quality_summaries if item.quality_type == "ORANGE_PEEL")
    assert orange.value == 88.5
    assert orange.reliability_status == VERIFIED
    assert orange.metrics
    assert any(item.metric_code == "doi" and item.value == 88.5 for item in orange.metrics)
    assert any(item.metric_code == "lw" for item in orange.metrics)
    assert len(detail.brush_contributions) == 1
    assert detail.brush_contributions[0].brush_no == "B01"
    assert detail.brush_contributions[0].coating_system == "CLEARCOAT"
    assert detail.brush_contributions[0].contribution_source == "LEGACY"
    assert detail.brush_contributions[0].parameters[0].configured_value == 280
    db.close()


def test_body_map_ignores_invalid_measurements() -> None:
    db = build_session()
    context = build_body_map_context(db)
    point = context["point"]
    run = context["run"]

    upsert_body_map_layout(
        point.id,
        BodyMapLayoutUpsert(body_view="SIDE", layout_x=0.4, layout_y=0.5),
        db,
    )
    create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-INVALID",
            production_run_id=run.id,
            measurement_point_id=point.id,
            quality_type="THICKNESS",
            measured_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
            is_valid=False,
            metrics=[
                QualityMetricInput(
                    metric_code="thickness_total",
                    metric_name="总膜厚",
                    raw_value=120.0,
                )
            ],
        ),
        db,
    )

    body_map = get_body_map(
        vehicle_model_id=context["model"].id,
        body_view="SIDE",
        production_run_id=run.id,
        db=db,
    )
    mapped = next(item for item in body_map.points if item.measurement_point_id == point.id)
    thickness = next(item for item in mapped.quality_summaries if item.quality_type == "THICKNESS")
    assert thickness.value is None
    assert thickness.judgement is None
    assert body_map.fail_count == 0
    db.close()


def test_body_map_defaults_to_latest_production_run() -> None:
    db = build_session()
    context = build_body_map_context(db)
    model = context["model"]
    point = context["point"]
    older = context["run"]
    newer = create_production_run(
        ProductionRunCreate(
            run_no="RUN-BM-2",
            body_no="BODY-BM-2",
            factory_id=context["factory"].id,
            vehicle_model_id=model.id,
            color_id=context["color"].id,
            started_at=datetime(2026, 7, 11, 8, 0, tzinfo=UTC),
        ),
        db,
    )
    upsert_body_map_layout(
        point.id,
        BodyMapLayoutUpsert(body_view="SIDE", layout_x=0.4, layout_y=0.5),
        db,
    )
    older_measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-OLD",
            production_run_id=older.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=70.0)],
        ),
        db,
    )
    newer_measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-NEW",
            production_run_id=newer.id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=datetime(2026, 7, 11, 9, 0, tzinfo=UTC),
            metrics=[QualityMetricInput(metric_code="doi", metric_name="DOI", raw_value=91.0)],
        ),
        db,
    )
    mark_verified(db, older_measurement["id"])
    mark_verified(db, newer_measurement["id"])

    body_map = get_body_map(vehicle_model_id=model.id, body_view="SIDE", db=db)
    assert body_map.production_run_id == newer.id
    assert body_map.production_run_no == "RUN-BM-2"
    mapped = next(item for item in body_map.points if item.measurement_point_id == point.id)
    orange = next(item for item in mapped.quality_summaries if item.quality_type == "ORANGE_PEEL")
    assert orange.value == 91.0
    db.close()


def test_body_map_fail_count_only_counts_placed_points() -> None:
    db = build_session()
    context = build_body_map_context(db)
    model = context["model"]
    part = context["part"]
    run = context["run"]
    unplaced = create_measurement_point(
        MeasurementPointCreate(
            code="PT-UNPLACED",
            name="Unplaced Fail",
            vehicle_model_id=model.id,
            part_id=part.id,
            point_type="QUALITY",
            region="Hood",
            quality_types=["THICKNESS"],
        ),
        db,
    )
    upsert_body_map_layout(
        context["point"].id,
        BodyMapLayoutUpsert(body_view="SIDE", layout_x=0.3, layout_y=0.4),
        db,
    )
    measurement = create_quality_measurement(
        QualityMeasurementCreate(
            data_no="QM-UNPLACED",
            production_run_id=run.id,
            measurement_point_id=unplaced.id,
            quality_type="THICKNESS",
            measured_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
            metrics=[
                QualityMetricInput(
                    metric_code="thickness_total",
                    metric_name="总膜厚",
                    raw_value=10.0,
                )
            ],
        ),
        db,
    )
    mark_verified(db, measurement["id"])
    body_map = get_body_map(
        vehicle_model_id=model.id,
        body_view="SIDE",
        production_run_id=run.id,
        db=db,
    )
    assert body_map.placed_count == 1
    unplaced_item = next(
        item for item in body_map.points if item.measurement_point_id == unplaced.id
    )
    assert unplaced_item.layout_x is None
    placed_fails = sum(
        1
        for item in body_map.points
        if item.layout_x is not None
        and any(summary.judgement == "FAIL" for summary in item.quality_summaries)
    )
    assert body_map.fail_count == placed_fails
    db.close()


def test_body_map_detail_prefers_governed_contribution_and_actuals() -> None:
    db = build_session()
    context = build_body_map_context(db)
    model = context["model"]
    part = context["part"]
    run = context["run"]
    point = context["point"]

    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-GOV",
            name="Governed Clearcoat",
            factory_id=context["factory"].id,
            process_stage="CLEARCOAT_1",
            station_code="ST-GOV",
            station_name="Station Gov",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V1", vehicle_model_ids=[model.id]),
        db,
    )
    brush = create_brush(version.id, BrushCreate(brush_no="G01", brush_table_no="GT01", part_id=part.id), db)
    create_brush_parameter(
        brush.id,
        BrushParameterCreate(
            parameter_code="flow",
            parameter_name="流量",
            configured_value=300,
            unit="ml/min",
        ),
        db,
    )
    upsert_brush_point_contribution(
        brush.id,
        point.id,
        BrushPointContributionUpsert(overlap_ratio=0.1, contribution_weight=0.2),
        db,
    )
    contrib_version = create_contribution_version(
        PointContributionVersionCreate(
            program_version_id=version.id,
            target_family="ORANGE_PEEL",
            version="CV1",
            method="EXPERT",
            status="ACTIVE",
            approved_by="tester",
        ),
        db,
    )
    create_contribution_entry(
        PointContributionEntryCreate(
            contribution_version_id=contrib_version.id,
            measurement_point_id=point.id,
            brush_id=brush.id,
            overlap_ratio=0.55,
            contribution_weight=0.8,
            validation_score=0.9,
        ),
        db,
    )
    stage = create_production_stage_run(
        run.id,
        ProductionStageRunCreate(
            process_stage="CLEARCOAT_1",
            program_version_id=version.id,
            status="COMPLETED",
        ),
        db,
    )
    create_actual_parameter(
        stage.id,
        ActualParameterCreate(
            brush_id=brush.id,
            parameter_code="flow",
            actual_value=312.5,
            unit="ml/min",
            sampled_at=datetime(2026, 7, 10, 8, 30, tzinfo=UTC),
            source_system="TEST",
        ),
        db,
    )

    detail = get_body_map_point_detail(point.id, production_run_id=run.id, db=db)
    assert len(detail.brush_contributions) == 1
    item = detail.brush_contributions[0]
    assert item.contribution_source == "GOVERNED"
    assert item.brush_no == "G01"
    assert item.overlap_ratio == 0.55
    assert item.contribution_weight == 0.8
    assert item.target_family == "ORANGE_PEEL"
    assert item.validation_score == 0.9
    assert item.parameters[0].configured_value == 300
    assert item.parameters[0].actual_value == 312.5
    db.close()


def test_body_map_canvas_returns_four_views_and_model_images() -> None:
    from app.api.routes.body_map import get_body_map_canvas

    db = build_session()
    context = build_body_map_context(db)
    kunlun = create_vehicle_model(VehicleModelCreate(code="kunlun", name="昆仑"), db)
    part = create_part(
        PartCreate(code="KL-HOOD", name="Kunlun Hood", material="钢", region="外覆盖件"),
        db,
    )
    upsert_body_map_layout(
        context["point"].id,
        BodyMapLayoutUpsert(body_view="RIGHT", layout_x=0.2, layout_y=0.3),
        db,
    )
    canvas = get_body_map_canvas(vehicle_model_id=context["model"].id, db=db)
    assert canvas.view_order == ["RIGHT", "LEFT", "TOP", "REAR"]
    assert len(canvas.views) == 4
    assert {view.body_view for view in canvas.views} == {"RIGHT", "LEFT", "TOP", "REAR"}
    right = next(view for view in canvas.views if view.body_view == "RIGHT")
    assert right.placed_count == 1
    assert right.background_image_url == "/body-maps/side.jpg"
    left = next(view for view in canvas.views if view.body_view == "LEFT")
    assert left.background_image_url == "/body-maps/side-left.jpg"

    create_body_map_point(
        BodyMapPointCreate(
            vehicle_model_id=kunlun.id,
            body_view="LEFT",
            layout_x=0.4,
            layout_y=0.5,
            code="KL-1",
            name="Kunlun Point",
            part_id=part.id,
        ),
        db,
    )
    kunlun_canvas = get_body_map_canvas(vehicle_model_id=kunlun.id, db=db)
    by_view = {view.body_view: view for view in kunlun_canvas.views}
    assert by_view["RIGHT"].background_image_url == "/kunlun_rightside.jpg"
    assert by_view["LEFT"].background_image_url == "/kunlun_leftside.jpg"
    assert by_view["TOP"].background_image_url == "/kunlun_top.jpg"
    assert by_view["REAR"].background_image_url == "/kunlun_trunk.jpg"
    assert by_view["LEFT"].placed_count == 1
    db.close()
