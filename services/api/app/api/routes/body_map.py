"""Quality body-map APIs: BIW grid layout, quality overlay, brush drill-down."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.quality_metric_catalog import QUALITY_METRIC_CATALOG
from app.models.domain import (
    ActualParameter,
    Brush,
    BrushParameter,
    BrushPointContribution,
    MeasurementGroup,
    MeasurementGroupPoint,
    MeasurementPoint,
    MeasurementPointLayout,
    Part,
    PointContributionEntry,
    PointContributionVersion,
    ProcessStage,
    ProductionRun,
    ProductionStageRun,
    QualityMeasurement,
    QualityMetricValue,
    SprayProgram,
    SprayProgramVersion,
    VehicleModel,
)
from app.api.routes.master_data import (
    add_measurement_group_point,
    create_measurement_point,
)
from app.schemas.master_data import MeasurementGroupPointCreate, MeasurementPointCreate
from app.schemas.quality import (
    BodyMapBrushContribution,
    BodyMapBrushParameter,
    BodyMapCanvasResponse,
    BodyMapLayoutDeactivate,
    BodyMapLayoutRead,
    BodyMapLayoutUpsert,
    BodyMapPointCreate,
    BodyMapPointDetail,
    BodyMapPointItem,
    BodyMapQualitySummary,
    BodyMapResponse,
)
from app.services.measurement_reliability import VERIFIED
from app.services.quality_evaluation import evaluate_quality_measurement

router = APIRouter(prefix="/quality/body-map", tags=["quality-body-map"])

# Canonical BIW views. Legacy SIDE is accepted as an alias of RIGHT.
BODY_VIEWS = ("RIGHT", "LEFT", "TOP", "REAR")
BODY_VIEW_ORDER = list(BODY_VIEWS)
BODY_VIEW_LABELS = {
    "RIGHT": "右侧视图",
    "LEFT": "左侧视图",
    "TOP": "俯视图",
    "REAR": "后视图",
}
LEGACY_BODY_VIEW_ALIASES = {"SIDE": "RIGHT"}

DEFAULT_BODY_VIEW_IMAGES = {
    "RIGHT": "/body-maps/side.jpg",
    "LEFT": "/body-maps/side.jpg",
    "TOP": "/body-maps/top.jpg",
    "REAR": "/ms11_back.jpg",
}

# Per-model assets under apps/web/public (matched by vehicle_model.code, case-insensitive).
MODEL_BODY_VIEW_IMAGES: dict[str, dict[str, str]] = {
    "kunlun": {
        "RIGHT": "/kunlun_rightside.jpg",
        "LEFT": "/kunlun_leftside.jpg",
        "TOP": "/kunlun_top.jpg",
        "REAR": "/kunlun_trunk.jpg",
    },
    "昆仑": {
        "RIGHT": "/kunlun_rightside.jpg",
        "LEFT": "/kunlun_leftside.jpg",
        "TOP": "/kunlun_top.jpg",
        "REAR": "/kunlun_trunk.jpg",
    },
    "ms11": {
        "RIGHT": "/ms11_rightside.jpg",
        "LEFT": "/ms11_rightside.jpg",
        "TOP": "/body-maps/top.jpg",
        "REAR": "/ms11_back.jpg",
    },
}

DEFAULT_GRID_COLS = 48
DEFAULT_GRID_ROWS = 24

PRIMARY_METRIC_BY_TYPE = {
    "ORANGE_PEEL": "doi",
    "COLOR_DIFFERENCE": "det",
    "THICKNESS": "thickness_total",
}
QUALITY_TYPE_ORDER = ("THICKNESS", "COLOR_DIFFERENCE", "ORANGE_PEEL")

METRIC_NAME_BY_CODE = {item["code"]: item["name"] for item in QUALITY_METRIC_CATALOG}
METRIC_UNIT_BY_CODE = {item["code"]: item.get("unit") for item in QUALITY_METRIC_CATALOG}


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _coating_system(process_stage: str) -> str:
    if process_stage == ProcessStage.MIDCOAT_EXT.value:
        return "MIDCOAT"
    if process_stage in {ProcessStage.BASECOAT_1.value, ProcessStage.BASECOAT_2.value}:
        return "BASECOAT"
    return "CLEARCOAT"


def _validate_body_view(body_view: str) -> str:
    normalized = body_view.strip().upper()
    normalized = LEGACY_BODY_VIEW_ALIASES.get(normalized, normalized)
    if normalized not in BODY_VIEWS:
        raise HTTPException(
            status_code=422,
            detail="body_view 仅支持 RIGHT / LEFT / TOP / REAR（SIDE 视为 RIGHT）",
        )
    return normalized


def _layout_view_keys(body_view: str) -> tuple[str, ...]:
    """Canonical view plus legacy aliases that may still exist in stored layouts."""
    if body_view == "RIGHT":
        return ("RIGHT", "SIDE")
    return (body_view,)


def _resolve_body_view_image(vehicle_model_code: str, body_view: str) -> str:
    code = (vehicle_model_code or "").strip()
    lowered = code.lower()
    for key, images in MODEL_BODY_VIEW_IMAGES.items():
        if lowered == key.lower() or key.lower() in lowered:
            return images.get(body_view) or DEFAULT_BODY_VIEW_IMAGES[body_view]
    return DEFAULT_BODY_VIEW_IMAGES[body_view]


def _snap_grid(layout_x: float, layout_y: float) -> tuple[int, int]:
    col = min(DEFAULT_GRID_COLS - 1, max(0, int(layout_x * DEFAULT_GRID_COLS)))
    row = min(DEFAULT_GRID_ROWS - 1, max(0, int(layout_y * DEFAULT_GRID_ROWS)))
    return col, row


def _cell_center(grid_col: int, grid_row: int) -> tuple[float, float]:
    return (
        (grid_col + 0.5) / DEFAULT_GRID_COLS,
        (grid_row + 0.5) / DEFAULT_GRID_ROWS,
    )


def _normalize_layout_coords(
    layout_x: float,
    layout_y: float,
    grid_col: int | None,
    grid_row: int | None,
) -> tuple[float, float, int, int]:
    if grid_col is None or grid_row is None:
        grid_col, grid_row = _snap_grid(layout_x, layout_y)
    grid_col = min(DEFAULT_GRID_COLS - 1, max(0, int(grid_col)))
    grid_row = min(DEFAULT_GRID_ROWS - 1, max(0, int(grid_row)))
    snapped_x, snapped_y = _cell_center(grid_col, grid_row)
    return snapped_x, snapped_y, grid_col, grid_row


def _resolve_production_run(
    db: Session,
    vehicle_model_id: str,
    production_run_id: str | None,
) -> ProductionRun | None:
    if production_run_id:
        run = _required(db, ProductionRun, production_run_id, "生产事件")
        if run.vehicle_model_id != vehicle_model_id:
            raise HTTPException(status_code=422, detail="生产事件不属于所选车型")
        return run
    return db.scalar(
        select(ProductionRun)
        .where(ProductionRun.vehicle_model_id == vehicle_model_id)
        .order_by(ProductionRun.started_at.desc())
    )


def _latest_quality_summaries(
    db: Session,
    point_ids: set[str],
    *,
    production_run_id: str | None = None,
) -> dict[str, list[BodyMapQualitySummary]]:
    if not point_ids:
        return {}
    # Overlay only uses VERIFIED measurements so unverified/failed imports never paint teal.
    query = select(QualityMeasurement).where(
        QualityMeasurement.measurement_point_id.in_(point_ids),
        QualityMeasurement.is_valid.is_(True),
        QualityMeasurement.reliability_status == VERIFIED,
    )
    if production_run_id:
        query = query.where(QualityMeasurement.production_run_id == production_run_id)
    else:
        # Without a run scope, refuse cross-run bleed — callers should resolve latest run first.
        return {
            point_id: [
                BodyMapQualitySummary(
                    quality_type=quality_type,
                    metric_code=PRIMARY_METRIC_BY_TYPE.get(quality_type),
                    metric_name=METRIC_NAME_BY_CODE.get(
                        PRIMARY_METRIC_BY_TYPE.get(quality_type, ""),
                        PRIMARY_METRIC_BY_TYPE.get(quality_type),
                    ),
                    unit=METRIC_UNIT_BY_CODE.get(PRIMARY_METRIC_BY_TYPE.get(quality_type, "")),
                )
                for quality_type in QUALITY_TYPE_ORDER
            ]
            for point_id in point_ids
        }
    measurements = list(db.scalars(query.order_by(QualityMeasurement.measured_at.desc())))

    latest_by_point_type: dict[tuple[str, str], QualityMeasurement] = {}
    for measurement in measurements:
        key = (measurement.measurement_point_id, measurement.quality_type)
        if key not in latest_by_point_type:
            latest_by_point_type[key] = measurement

    measurement_ids = [item.id for item in latest_by_point_type.values()]
    metrics_by_measurement: dict[str, list[QualityMetricValue]] = defaultdict(list)
    if measurement_ids:
        for metric in db.scalars(
            select(QualityMetricValue).where(QualityMetricValue.measurement_id.in_(measurement_ids))
        ):
            metrics_by_measurement[metric.measurement_id].append(metric)

    result: dict[str, list[BodyMapQualitySummary]] = defaultdict(list)
    for (point_id, quality_type), measurement in latest_by_point_type.items():
        primary_code = PRIMARY_METRIC_BY_TYPE.get(quality_type)
        metrics = metrics_by_measurement.get(measurement.id, [])
        primary = next((item for item in metrics if item.metric_code == primary_code), None)
        if primary is None and metrics:
            primary = metrics[0]
        judgement = None
        try:
            evaluation = evaluate_quality_measurement(db, measurement, metrics)
            judgement = evaluation.get("judgement")
        except Exception:  # noqa: BLE001 - map overlay should not fail on evaluation edge cases
            judgement = None
        if not measurement.is_valid:
            judgement = "INVALID"
        result[point_id].append(
            BodyMapQualitySummary(
                quality_type=quality_type,
                metric_code=primary.metric_code if primary else primary_code,
                metric_name=(
                    primary.metric_name
                    if primary
                    else METRIC_NAME_BY_CODE.get(primary_code or "", primary_code)
                ),
                value=(
                    primary.corrected_value
                    if primary and primary.corrected_value is not None
                    else (primary.raw_value if primary else None)
                ),
                unit=primary.unit if primary else METRIC_UNIT_BY_CODE.get(primary_code or ""),
                measured_at=measurement.measured_at,
                data_no=measurement.data_no,
                judgement=judgement,
                reliability_status=measurement.reliability_status,
            )
        )
    for point_id in point_ids:
        existing_types = {item.quality_type for item in result.get(point_id, [])}
        for quality_type in QUALITY_TYPE_ORDER:
            if quality_type not in existing_types:
                result[point_id].append(
                    BodyMapQualitySummary(
                        quality_type=quality_type,
                        metric_code=PRIMARY_METRIC_BY_TYPE.get(quality_type),
                        metric_name=METRIC_NAME_BY_CODE.get(
                            PRIMARY_METRIC_BY_TYPE.get(quality_type, ""),
                            PRIMARY_METRIC_BY_TYPE.get(quality_type),
                        ),
                        unit=METRIC_UNIT_BY_CODE.get(PRIMARY_METRIC_BY_TYPE.get(quality_type, "")),
                    )
                )
        result[point_id].sort(
            key=lambda item: QUALITY_TYPE_ORDER.index(item.quality_type)
            if item.quality_type in QUALITY_TYPE_ORDER
            else 99
        )
    return result


def _risk_score(summaries: list[BodyMapQualitySummary]) -> float:
    score = 0.0
    for item in summaries:
        if item.judgement == "FAIL":
            score += 40
        elif item.judgement == "INVALID":
            score += 25
        elif item.judgement == "NO_STANDARD":
            score += 10
        elif item.value is None:
            score += 5
    return min(100.0, score)


def _parameter_cards(
    configured: list[BrushParameter],
    actual_by_code: dict[str, float],
) -> list[BodyMapBrushParameter]:
    codes = {item.parameter_code for item in configured} | set(actual_by_code)
    configured_by_code = {item.parameter_code: item for item in configured}
    cards: list[BodyMapBrushParameter] = []
    for code in sorted(codes):
        conf = configured_by_code.get(code)
        cards.append(
            BodyMapBrushParameter(
                parameter_code=code,
                parameter_name=conf.parameter_name if conf else code,
                configured_value=conf.configured_value if conf else None,
                actual_value=actual_by_code.get(code),
                unit=conf.unit if conf else "",
            )
        )
    return cards


def _brush_contributions_for_point(
    db: Session,
    point: MeasurementPoint,
    *,
    production_run_id: str | None = None,
) -> list[BodyMapBrushContribution]:
    stage_runs: list[ProductionStageRun] = []
    if production_run_id:
        stage_runs = list(
            db.scalars(
                select(ProductionStageRun).where(
                    ProductionStageRun.production_run_id == production_run_id
                )
            )
        )

    actual_by_brush_code: dict[tuple[str, str], float] = {}
    if stage_runs:
        stage_ids = [item.id for item in stage_runs]
        for actual in db.scalars(
            select(ActualParameter).where(
                ActualParameter.production_stage_run_id.in_(stage_ids),
                ActualParameter.brush_id.is_not(None),
            )
        ):
            if actual.brush_id:
                actual_by_brush_code[(actual.brush_id, actual.parameter_code)] = actual.actual_value

    brush_items: list[BodyMapBrushContribution] = []
    seen_keys: set[tuple[str, str, str]] = set()

    target_families = [
        family
        for family in QUALITY_TYPE_ORDER
        if not point.quality_types or family in set(point.quality_types)
    ] or list(QUALITY_TYPE_ORDER)

    if stage_runs:
        for stage_run in stage_runs:
            for target_family in target_families:
                contribution_version = db.scalar(
                    select(PointContributionVersion)
                    .where(
                        PointContributionVersion.program_version_id
                        == stage_run.program_version_id,
                        PointContributionVersion.target_family == target_family,
                        PointContributionVersion.status == "ACTIVE",
                    )
                    .order_by(PointContributionVersion.approved_at.desc())
                )
                if not contribution_version:
                    continue
                entries = list(
                    db.scalars(
                        select(PointContributionEntry).where(
                            PointContributionEntry.contribution_version_id
                            == contribution_version.id,
                            PointContributionEntry.measurement_point_id == point.id,
                            PointContributionEntry.brush_id.is_not(None),
                        )
                    )
                )
                if not entries:
                    continue
                brush_ids = {entry.brush_id for entry in entries if entry.brush_id}
                brushes = {
                    item.id: item
                    for item in db.scalars(
                        select(Brush).where(Brush.id.in_(brush_ids or {"__none__"}))
                    )
                }
                parameters_by_brush: dict[str, list[BrushParameter]] = defaultdict(list)
                for parameter in db.scalars(
                    select(BrushParameter)
                    .where(BrushParameter.brush_id.in_(brush_ids or {"__none__"}))
                    .order_by(BrushParameter.parameter_code)
                ):
                    parameters_by_brush[parameter.brush_id].append(parameter)
                version = db.get(SprayProgramVersion, stage_run.program_version_id)
                program = (
                    db.get(SprayProgram, version.spray_program_id) if version else None
                )
                process_stage = program.process_stage if program else stage_run.process_stage
                for entry in entries:
                    brush = brushes.get(entry.brush_id or "")
                    if not brush:
                        continue
                    dedupe_key = (brush.id, process_stage, target_family)
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)
                    actual_codes = {
                        code: value
                        for (brush_id, code), value in actual_by_brush_code.items()
                        if brush_id == brush.id
                    }
                    brush_items.append(
                        BodyMapBrushContribution(
                            brush_id=brush.id,
                            brush_no=brush.brush_no,
                            brush_table_no=brush.brush_table_no,
                            process_stage=process_stage,
                            coating_system=_coating_system(process_stage),
                            overlap_ratio=entry.overlap_ratio,
                            contribution_weight=entry.contribution_weight,
                            source=contribution_version.method,
                            version=contribution_version.version,
                            is_approved=True,
                            contribution_source="GOVERNED",
                            target_family=target_family,
                            validation_score=entry.validation_score,
                            path_segment_id=entry.path_segment_id,
                            parameters=_parameter_cards(
                                parameters_by_brush.get(brush.id, []),
                                actual_codes,
                            ),
                        )
                    )

    if brush_items:
        brush_items.sort(
            key=lambda item: (
                {"MIDCOAT": 0, "BASECOAT": 1, "CLEARCOAT": 2}.get(item.coating_system, 9),
                item.brush_no,
                item.target_family or "",
            )
        )
        return brush_items

    # Legacy fallback: approved BrushPointContribution rows for the point.
    contributions = list(
        db.scalars(
            select(BrushPointContribution).where(
                BrushPointContribution.measurement_point_id == point.id
            )
        )
    )
    brush_ids = {item.brush_id for item in contributions}
    brushes = {
        item.id: item
        for item in db.scalars(select(Brush).where(Brush.id.in_(brush_ids or {"__none__"})))
    }
    version_ids = {brush.program_version_id for brush in brushes.values()}
    versions = {
        item.id: item
        for item in db.scalars(
            select(SprayProgramVersion).where(
                SprayProgramVersion.id.in_(version_ids or {"__none__"})
            )
        )
    }
    program_ids = {version.spray_program_id for version in versions.values()}
    programs = {
        item.id: item
        for item in db.scalars(
            select(SprayProgram).where(SprayProgram.id.in_(program_ids or {"__none__"}))
        )
    }
    parameters_by_brush: dict[str, list[BrushParameter]] = defaultdict(list)
    for parameter in db.scalars(
        select(BrushParameter)
        .where(BrushParameter.brush_id.in_(brush_ids or {"__none__"}))
        .order_by(BrushParameter.parameter_code)
    ):
        parameters_by_brush[parameter.brush_id].append(parameter)

    for contribution in contributions:
        brush = brushes.get(contribution.brush_id)
        if not brush:
            continue
        version = versions.get(brush.program_version_id)
        program = programs.get(version.spray_program_id) if version else None
        process_stage = program.process_stage if program else "UNKNOWN"
        actual_codes = {
            code: value
            for (brush_id, code), value in actual_by_brush_code.items()
            if brush_id == brush.id
        }
        brush_items.append(
            BodyMapBrushContribution(
                brush_id=brush.id,
                brush_no=brush.brush_no,
                brush_table_no=brush.brush_table_no,
                process_stage=process_stage,
                coating_system=_coating_system(process_stage)
                if process_stage != "UNKNOWN"
                else "UNKNOWN",
                overlap_ratio=contribution.overlap_ratio,
                contribution_weight=contribution.contribution_weight,
                source=contribution.source,
                version=contribution.version,
                is_approved=contribution.is_approved,
                contribution_source="LEGACY",
                parameters=_parameter_cards(
                    parameters_by_brush.get(brush.id, []),
                    actual_codes,
                ),
            )
        )
    brush_items.sort(
        key=lambda item: (
            {"MIDCOAT": 0, "BASECOAT": 1, "CLEARCOAT": 2}.get(item.coating_system, 9),
            item.brush_no,
        )
    )
    return brush_items


def _upsert_layout(
    db: Session,
    *,
    measurement_point_id: str,
    body_view: str,
    layout_x: float,
    layout_y: float,
    grid_col: int | None,
    grid_row: int | None,
) -> MeasurementPointLayout:
    layout_x, layout_y, grid_col, grid_row = _normalize_layout_coords(
        layout_x, layout_y, grid_col, grid_row
    )
    view_keys = _layout_view_keys(body_view)
    layouts = list(
        db.scalars(
            select(MeasurementPointLayout).where(
                MeasurementPointLayout.measurement_point_id == measurement_point_id,
                MeasurementPointLayout.body_view.in_(view_keys),
            )
        )
    )
    layout = next((item for item in layouts if item.body_view == body_view), None)
    if layout is None and layouts:
        layout = layouts[0]
    # Soft-retire legacy alias rows when migrating SIDE → RIGHT.
    for item in layouts:
        if item is layout:
            continue
        if item.body_view != body_view and item.status == "ACTIVE":
            item.status = "INACTIVE"
    if layout:
        layout.body_view = body_view
        layout.layout_x = layout_x
        layout.layout_y = layout_y
        layout.grid_col = grid_col
        layout.grid_row = grid_row
        layout.status = "ACTIVE"
    else:
        layout = MeasurementPointLayout(
            measurement_point_id=measurement_point_id,
            body_view=body_view,
            layout_x=layout_x,
            layout_y=layout_y,
            grid_col=grid_col,
            grid_row=grid_row,
            status="ACTIVE",
        )
        db.add(layout)
    db.commit()
    db.refresh(layout)
    return layout


def _build_body_map_response(
    db: Session,
    *,
    model: VehicleModel,
    body_view: str,
    measurement_group_id: str | None,
    production_run_id: str | None,
    points: list[MeasurementPoint] | None = None,
    group_point_ids: set[str] | None = None,
    layouts_by_point: dict[str, MeasurementPointLayout] | None = None,
    parts: dict[str, Part] | None = None,
    summaries: dict[str, list[BodyMapQualitySummary]] | None = None,
    resolved_run: ProductionRun | None = None,
) -> BodyMapResponse:
    view = _validate_body_view(body_view)
    if resolved_run is None:
        resolved_run = _resolve_production_run(db, model.id, production_run_id)
    resolved_run_id = resolved_run.id if resolved_run else None

    if group_point_ids is None:
        group_point_ids = set()
        if measurement_group_id:
            group = _required(db, MeasurementGroup, measurement_group_id, "测量编组")
            if group.vehicle_model_id != model.id:
                raise HTTPException(status_code=422, detail="测量编组不属于所选车型")
            group_point_ids = set(
                db.scalars(
                    select(MeasurementGroupPoint.measurement_point_id).where(
                        MeasurementGroupPoint.measurement_group_id == measurement_group_id
                    )
                )
            )

    if points is None:
        points = list(
            db.scalars(
                select(MeasurementPoint)
                .where(
                    MeasurementPoint.vehicle_model_id == model.id,
                    MeasurementPoint.point_type == "QUALITY",
                )
                .order_by(MeasurementPoint.code)
            )
        )
    point_ids = {point.id for point in points}

    if layouts_by_point is None:
        view_keys = _layout_view_keys(view)
        layouts_by_point = {}
        for item in db.scalars(
            select(MeasurementPointLayout).where(
                MeasurementPointLayout.measurement_point_id.in_(point_ids or {"__none__"}),
                MeasurementPointLayout.body_view.in_(view_keys),
                MeasurementPointLayout.status == "ACTIVE",
            )
        ):
            existing = layouts_by_point.get(item.measurement_point_id)
            if existing is None or item.body_view == view:
                layouts_by_point[item.measurement_point_id] = item

    if parts is None:
        parts = {
            item.id: item
            for item in db.scalars(
                select(Part).where(Part.id.in_({point.part_id for point in points} or {"__none__"}))
            )
        }

    if summaries is None:
        summaries = _latest_quality_summaries(
            db, point_ids, production_run_id=resolved_run_id
        )

    items: list[BodyMapPointItem] = []
    for point in points:
        layout = layouts_by_point.get(point.id)
        part = parts.get(point.part_id)
        point_summaries = summaries.get(point.id, [])
        items.append(
            BodyMapPointItem(
                measurement_point_id=point.id,
                layout_id=layout.id if layout else None,
                code=point.code,
                name=point.name,
                part_id=point.part_id,
                part_code=part.code if part else None,
                part_name=part.name if part else None,
                region=point.region,
                quality_types=list(point.quality_types or []),
                layout_x=layout.layout_x if layout else None,
                layout_y=layout.layout_y if layout else None,
                grid_col=layout.grid_col if layout else None,
                grid_row=layout.grid_row if layout else None,
                in_group=(point.id in group_point_ids) if measurement_group_id else True,
                quality_summaries=point_summaries,
                risk_score=_risk_score(point_summaries),
            )
        )

    placed_count = sum(1 for item in items if item.layout_x is not None)
    group_point_count = (
        sum(1 for item in items if item.in_group) if measurement_group_id else len(items)
    )
    fail_count = sum(
        1
        for item in items
        if item.layout_x is not None
        and any(summary.judgement == "FAIL" for summary in item.quality_summaries)
    )

    return BodyMapResponse(
        vehicle_model_id=model.id,
        vehicle_model_code=model.code,
        vehicle_model_name=model.name,
        body_view=view,
        background_image_url=_resolve_body_view_image(model.code, view),
        grid_cols=DEFAULT_GRID_COLS,
        grid_rows=DEFAULT_GRID_ROWS,
        measurement_group_id=measurement_group_id,
        production_run_id=resolved_run_id,
        production_run_no=resolved_run.run_no if resolved_run else None,
        quality_scope="VERIFIED",
        placed_count=placed_count,
        group_point_count=group_point_count,
        fail_count=fail_count,
        points=items,
    )


@router.get("", response_model=BodyMapResponse)
def get_body_map(
    vehicle_model_id: str,
    body_view: str = "RIGHT",
    measurement_group_id: str | None = None,
    production_run_id: str | None = None,
    db: Session = Depends(get_db),
) -> BodyMapResponse:
    model = _required(db, VehicleModel, vehicle_model_id, "车型")
    return _build_body_map_response(
        db,
        model=model,
        body_view=body_view,
        measurement_group_id=measurement_group_id,
        production_run_id=production_run_id,
    )


@router.get("/canvas", response_model=BodyMapCanvasResponse)
def get_body_map_canvas(
    vehicle_model_id: str,
    measurement_group_id: str | None = None,
    production_run_id: str | None = None,
    db: Session = Depends(get_db),
) -> BodyMapCanvasResponse:
    model = _required(db, VehicleModel, vehicle_model_id, "车型")
    resolved_run = _resolve_production_run(db, model.id, production_run_id)
    resolved_run_id = resolved_run.id if resolved_run else None

    group_point_ids: set[str] = set()
    if measurement_group_id:
        group = _required(db, MeasurementGroup, measurement_group_id, "测量编组")
        if group.vehicle_model_id != model.id:
            raise HTTPException(status_code=422, detail="测量编组不属于所选车型")
        group_point_ids = set(
            db.scalars(
                select(MeasurementGroupPoint.measurement_point_id).where(
                    MeasurementGroupPoint.measurement_group_id == measurement_group_id
                )
            )
        )

    points = list(
        db.scalars(
            select(MeasurementPoint)
            .where(
                MeasurementPoint.vehicle_model_id == model.id,
                MeasurementPoint.point_type == "QUALITY",
            )
            .order_by(MeasurementPoint.code)
        )
    )
    point_ids = {point.id for point in points}
    parts = {
        item.id: item
        for item in db.scalars(
            select(Part).where(Part.id.in_({point.part_id for point in points} or {"__none__"}))
        )
    }
    summaries = _latest_quality_summaries(db, point_ids, production_run_id=resolved_run_id)

    all_view_keys = tuple({key for view in BODY_VIEW_ORDER for key in _layout_view_keys(view)})
    layouts_rows = list(
        db.scalars(
            select(MeasurementPointLayout).where(
                MeasurementPointLayout.measurement_point_id.in_(point_ids or {"__none__"}),
                MeasurementPointLayout.body_view.in_(all_view_keys),
                MeasurementPointLayout.status == "ACTIVE",
            )
        )
    )

    views: list[BodyMapResponse] = []
    for view in BODY_VIEW_ORDER:
        view_keys = set(_layout_view_keys(view))
        layouts_by_point: dict[str, MeasurementPointLayout] = {}
        for item in layouts_rows:
            if item.body_view not in view_keys:
                continue
            existing = layouts_by_point.get(item.measurement_point_id)
            if existing is None or item.body_view == view:
                layouts_by_point[item.measurement_point_id] = item
        views.append(
            _build_body_map_response(
                db,
                model=model,
                body_view=view,
                measurement_group_id=measurement_group_id,
                production_run_id=resolved_run_id,
                points=points,
                group_point_ids=group_point_ids,
                layouts_by_point=layouts_by_point,
                parts=parts,
                summaries=summaries,
                resolved_run=resolved_run,
            )
        )

    total_placed = sum(view.placed_count for view in views)
    # Fail once per point if any placed view shows FAIL.
    fail_point_ids = {
        item.measurement_point_id
        for view in views
        for item in view.points
        if item.layout_x is not None
        and any(summary.judgement == "FAIL" for summary in item.quality_summaries)
    }
    group_point_count = (
        len(group_point_ids) if measurement_group_id else len(points)
    )

    return BodyMapCanvasResponse(
        vehicle_model_id=model.id,
        vehicle_model_code=model.code,
        vehicle_model_name=model.name,
        view_order=list(BODY_VIEW_ORDER),
        view_labels=dict(BODY_VIEW_LABELS),
        grid_cols=DEFAULT_GRID_COLS,
        grid_rows=DEFAULT_GRID_ROWS,
        measurement_group_id=measurement_group_id,
        production_run_id=resolved_run_id,
        production_run_no=resolved_run.run_no if resolved_run else None,
        quality_scope="VERIFIED",
        placed_count=total_placed,
        group_point_count=group_point_count,
        fail_count=len(fail_point_ids),
        views=views,
    )


@router.put(
    "/layouts/{measurement_point_id}",
    response_model=BodyMapLayoutRead,
)
def upsert_body_map_layout(
    measurement_point_id: str,
    payload: BodyMapLayoutUpsert,
    db: Session = Depends(get_db),
) -> MeasurementPointLayout:
    point = _required(db, MeasurementPoint, measurement_point_id, "测量点")
    if point.point_type != "QUALITY":
        raise HTTPException(status_code=422, detail="仅质量测量点可落在车身点位图")
    view = _validate_body_view(payload.body_view)
    layout = _upsert_layout(
        db,
        measurement_point_id=point.id,
        body_view=view,
        layout_x=payload.layout_x,
        layout_y=payload.layout_y,
        grid_col=payload.grid_col,
        grid_row=payload.grid_row,
    )
    return layout


@router.post(
    "/points",
    response_model=BodyMapPointItem,
    status_code=status.HTTP_201_CREATED,
)
def create_body_map_point(
    payload: BodyMapPointCreate,
    db: Session = Depends(get_db),
) -> BodyMapPointItem:
    view = _validate_body_view(payload.body_view)
    _required(db, VehicleModel, payload.vehicle_model_id, "车型")
    _required(db, Part, payload.part_id, "零件")
    quality_types = payload.quality_types or list(QUALITY_TYPE_ORDER)
    point = create_measurement_point(
        MeasurementPointCreate(
            code=payload.code,
            name=payload.name,
            vehicle_model_id=payload.vehicle_model_id,
            part_id=payload.part_id,
            point_type=payload.point_type,
            region=payload.region,
            quality_types=quality_types,
            is_match_point=False,
        ),
        db,
    )
    layout = _upsert_layout(
        db,
        measurement_point_id=point.id,
        body_view=view,
        layout_x=payload.layout_x,
        layout_y=payload.layout_y,
        grid_col=payload.grid_col,
        grid_row=payload.grid_row,
    )
    in_group = False
    if payload.measurement_group_id:
        group = _required(db, MeasurementGroup, payload.measurement_group_id, "测量编组")
        if group.vehicle_model_id != payload.vehicle_model_id:
            raise HTTPException(status_code=422, detail="测量编组不属于所选车型")
        add_measurement_group_point(
            payload.measurement_group_id,
            MeasurementGroupPointCreate(measurement_point_id=point.id, sequence_no=0),
            db,
        )
        in_group = True
    part = db.get(Part, point.part_id)
    return BodyMapPointItem(
        measurement_point_id=point.id,
        layout_id=layout.id,
        code=point.code,
        name=point.name,
        part_id=point.part_id,
        part_code=part.code if part else None,
        part_name=part.name if part else None,
        region=point.region,
        quality_types=list(point.quality_types or []),
        layout_x=layout.layout_x,
        layout_y=layout.layout_y,
        grid_col=layout.grid_col,
        grid_row=layout.grid_row,
        in_group=in_group or payload.measurement_group_id is None,
        quality_summaries=[],
        risk_score=0,
    )


@router.post(
    "/layouts/{layout_id}/deactivate",
    response_model=BodyMapLayoutRead,
)
def deactivate_body_map_layout(
    layout_id: str,
    payload: BodyMapLayoutDeactivate | None = None,
    db: Session = Depends(get_db),
) -> MeasurementPointLayout:
    layout = _required(db, MeasurementPointLayout, layout_id, "点位布局")
    if payload and payload.body_view:
        view = _validate_body_view(payload.body_view)
        layout_view = LEGACY_BODY_VIEW_ALIASES.get(layout.body_view.upper(), layout.body_view.upper())
        if layout_view != view:
            raise HTTPException(status_code=422, detail="布局视图与请求不一致")
    layout.status = "INACTIVE"
    db.commit()
    db.refresh(layout)
    return layout


@router.get(
    "/points/{measurement_point_id}/detail",
    response_model=BodyMapPointDetail,
)
def get_body_map_point_detail(
    measurement_point_id: str,
    production_run_id: str | None = None,
    db: Session = Depends(get_db),
) -> BodyMapPointDetail:
    point = _required(db, MeasurementPoint, measurement_point_id, "测量点")
    part = db.get(Part, point.part_id)
    resolved_run = _resolve_production_run(db, point.vehicle_model_id, production_run_id)
    resolved_run_id = resolved_run.id if resolved_run else None
    summaries = _latest_quality_summaries(
        db, {point.id}, production_run_id=resolved_run_id
    ).get(point.id, [])
    brush_items = _brush_contributions_for_point(
        db, point, production_run_id=resolved_run_id
    )

    return BodyMapPointDetail(
        measurement_point_id=point.id,
        code=point.code,
        name=point.name,
        part_id=point.part_id,
        part_code=part.code if part else None,
        part_name=part.name if part else None,
        region=point.region,
        quality_types=list(point.quality_types or []),
        quality_summaries=summaries,
        brush_contributions=brush_items,
    )
