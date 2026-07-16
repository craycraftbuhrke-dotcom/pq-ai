"""Tests for 3D body-map scene and layout projection."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.body_map import (
    deactivate_body_map_3d_layout,
    get_body_map_3d_scene,
    upsert_body_map_3d_layout,
)
from app.api.routes.master_data import (
    create_measurement_group,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.models.domain import MeasurementPoint3DLayout, MeasurementPointLayout
from app.schemas.master_data import (
    MeasurementGroupCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelCreate,
)
from app.schemas.quality import BodyMap3DLayoutUpsert
from app.services.body_map_3d_projection import (
    DEFAULT_BOUNDS,
    project_point_to_all_views,
    project_point_to_view,
)
from tests.schema_guard import create_transient_test_schema


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def test_projection_center_is_unclamped():
    cx = (DEFAULT_BOUNDS.min_x + DEFAULT_BOUNDS.max_x) / 2
    cy = (DEFAULT_BOUNDS.min_y + DEFAULT_BOUNDS.max_y) / 2
    cz = (DEFAULT_BOUNDS.min_z + DEFAULT_BOUNDS.max_z) / 2
    for view in ("RIGHT", "LEFT", "TOP", "REAR"):
        x, y, clamped = project_point_to_view(
            pos_x=cx, pos_y=cy, pos_z=cz, body_view=view
        )
        assert 0 < x < 1
        assert 0 < y < 1
        assert clamped is False


def test_projection_outside_bounds_clamps():
    projections = project_point_to_all_views(
        pos_x=DEFAULT_BOUNDS.max_x + 5,
        pos_y=DEFAULT_BOUNDS.max_y + 5,
        pos_z=DEFAULT_BOUNDS.max_z + 5,
    )
    for view, proj in projections.items():
        assert 0 <= proj["layout_x"] <= 1
        assert 0 <= proj["layout_y"] <= 1
        assert proj["projected_clamped"] is True, f"{view} should be clamped"


def test_3d_scene_returns_points_without_layout():
    db = _build_session()
    try:
        model = create_vehicle_model(
            VehicleModelCreate(code="MS11", name="SU7"),
            db,
        )
        part = create_part(PartCreate(code="DOOR", name="Door"), db)
        create_measurement_point(
            MeasurementPointCreate(
                vehicle_model_id=model.id,
                code="P001",
                name="Front Door",
                part_id=part.id,
            ),
            db,
        )
        scene = get_body_map_3d_scene(vehicle_model_id=model.id, db=db)
        assert scene.vehicle_model_code == "MS11"
        assert len(scene.points) == 1
        assert scene.points[0].pos_x is None
        assert scene.points[0].has_2d_only is False
        assert scene.placed_count == 0
    finally:
        db.close()


def test_upsert_3d_layout_and_project_to_2d():
    db = _build_session()
    try:
        model = create_vehicle_model(
            VehicleModelCreate(code="MS11", name="SU7"),
            db,
        )
        part = create_part(PartCreate(code="DOOR", name="Door"), db)
        point = create_measurement_point(
            MeasurementPointCreate(
                vehicle_model_id=model.id,
                code="P001",
                name="Front Door",
                part_id=part.id,
            ),
            db,
        )

        result = upsert_body_map_3d_layout(
            point.id,
            BodyMap3DLayoutUpsert(
                pos_x=0.0,
                pos_y=0.8,
                pos_z=0.5,
                project_to_2d=True,
            ),
            db,
        )
        assert result.status == "ACTIVE"
        assert result.projected_views  # four views projected
        assert set(result.projected_views.keys()) == {"RIGHT", "LEFT", "TOP", "REAR"}

        # 2D layouts should now exist for all four views
        layouts = list(
            db.scalars(
                __import__("sqlalchemy").select(MeasurementPointLayout).where(
                    MeasurementPointLayout.measurement_point_id == point.id,
                    MeasurementPointLayout.status == "ACTIVE",
                )
            )
        )
        assert len(layouts) == 4

        # Scene should show the point as placed
        scene = get_body_map_3d_scene(vehicle_model_id=model.id, db=db)
        assert scene.placed_count == 1
        assert scene.points[0].pos_x == 0.0
        assert scene.points[0].pos_y == 0.8
        assert scene.points[0].pos_z == 0.5
        assert scene.points[0].has_2d_only is False
    finally:
        db.close()


def test_deactivate_3d_syncs_2d():
    db = _build_session()
    try:
        model = create_vehicle_model(
            VehicleModelCreate(code="MS11", name="SU7"),
            db,
        )
        part = create_part(PartCreate(code="DOOR", name="Door"), db)
        point = create_measurement_point(
            MeasurementPointCreate(
                vehicle_model_id=model.id,
                code="P001",
                name="Front Door",
                part_id=part.id,
            ),
            db,
        )
        result = upsert_body_map_3d_layout(
            point.id,
            BodyMap3DLayoutUpsert(pos_x=0, pos_y=0.5, pos_z=0, project_to_2d=True),
            db,
        )
        active_2d = list(
            db.scalars(
                __import__("sqlalchemy").select(MeasurementPointLayout).where(
                    MeasurementPointLayout.measurement_point_id == point.id,
                    MeasurementPointLayout.status == "ACTIVE",
                )
            )
        )
        assert len(active_2d) == 4

        deactivated = deactivate_body_map_3d_layout(result.id, db)
        assert deactivated.status == "INACTIVE"

        remaining_active_2d = list(
            db.scalars(
                __import__("sqlalchemy").select(MeasurementPointLayout).where(
                    MeasurementPointLayout.measurement_point_id == point.id,
                    MeasurementPointLayout.status == "ACTIVE",
                )
            )
        )
        assert len(remaining_active_2d) == 0
    finally:
        db.close()
