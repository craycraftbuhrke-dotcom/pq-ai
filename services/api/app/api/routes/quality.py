from collections import defaultdict
from statistics import mean, pstdev

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.quality_metric_catalog import QUALITY_METRIC_CATALOG
from app.domain.scope_policy import (
    APPROVED_METRIC_KEYS,
    APPROVED_QUALITY_TYPES,
    ScopeViolation,
    require_approved_metric,
    require_approved_metrics,
    require_approved_quality_type,
)
from app.models.domain import (
    Color,
    MeasurementGroup,
    MeasurementPoint,
    Part,
    ProductionRun,
    QualityMeasurement,
    QualityMetricDefinition,
    QualityMetricValue,
    QualityStandard,
    VehicleModel,
)
from app.schemas.quality import (
    QualityMeasurementCreate,
    QualityAnalytics,
    QualityMeasurementRead,
    QualityMeasurementUpdate,
    QualityMetricDefinitionRead,
    QualityStandardCreate,
    QualityStandardRead,
    QualityStandardUpdate,
    QualitySummary,
)
from app.services.quality_evaluation import evaluate_quality_measurement

router = APIRouter(prefix="/quality", tags=["quality-data"])


def _validate_quality_scope(quality_type: str, metric_codes: list[str]) -> None:
    try:
        require_approved_metrics(quality_type, metric_codes)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _measurement_dict(
    measurement: QualityMeasurement,
    metrics: list[QualityMetricValue],
    point: MeasurementPoint,
    evaluation: dict,
) -> dict:
    return {
        "id": measurement.id,
        "created_at": measurement.created_at,
        "updated_at": measurement.updated_at,
        "data_no": measurement.data_no,
        "production_run_id": measurement.production_run_id,
        "measurement_group_id": measurement.measurement_group_id,
        "measurement_point_id": measurement.measurement_point_id,
        "measurement_point_code": point.code,
        "measurement_point_name": point.name,
        "quality_type": measurement.quality_type,
        "data_type": measurement.data_type,
        "measured_at": measurement.measured_at,
        "measured_by": measurement.measured_by,
        "device_code": measurement.device_code,
        "status_score": measurement.status_score,
        "is_valid": measurement.is_valid,
        "judgement": evaluation["judgement"],
        "violations": evaluation["violations"],
        "metrics": metrics,
    }


def _measurement_result(db: Session, measurement: QualityMeasurement) -> dict:
    metrics = list(
        db.scalars(
            select(QualityMetricValue)
            .where(QualityMetricValue.measurement_id == measurement.id)
            .order_by(QualityMetricValue.metric_code)
        )
    )
    metrics = [
        metric
        for metric in metrics
        if (measurement.quality_type, metric.metric_code) in APPROVED_METRIC_KEYS
    ]
    point = _required(db, MeasurementPoint, measurement.measurement_point_id, "测量点")
    return _measurement_dict(
        measurement,
        metrics,
        point,
        evaluate_quality_measurement(db, measurement, metrics),
    )


@router.get("/summary", response_model=QualitySummary)
def quality_summary(db: Session = Depends(get_db)) -> dict:
    measurements = list(
        db.scalars(
            select(QualityMeasurement).where(
                QualityMeasurement.quality_type.in_(APPROVED_QUALITY_TYPES)
            )
        )
    )
    judgements = []
    metric_value_count = 0
    for measurement in measurements:
        metrics = list(
            db.scalars(
                select(QualityMetricValue).where(
                    QualityMetricValue.measurement_id == measurement.id
                )
            )
        )
        metrics = [
            metric
            for metric in metrics
            if (measurement.quality_type, metric.metric_code) in APPROVED_METRIC_KEYS
        ]
        metric_value_count += len(metrics)
        judgements.append(evaluate_quality_measurement(db, measurement, metrics)["judgement"])
    by_type = {
        quality_type: count
        for quality_type, count in db.execute(
            select(QualityMeasurement.quality_type, func.count())
            .where(QualityMeasurement.quality_type.in_(APPROVED_QUALITY_TYPES))
            .group_by(QualityMeasurement.quality_type)
        )
    }
    return {
        "measurements": len(measurements),
        "valid_measurements": int(
            db.scalar(
                select(func.count())
                .select_from(QualityMeasurement)
                .where(
                    QualityMeasurement.quality_type.in_(APPROVED_QUALITY_TYPES),
                    QualityMeasurement.is_valid.is_(True),
                )
            )
            or 0
        ),
        "metric_values": metric_value_count,
        "standards": int(
            db.scalar(
                select(func.count())
                .select_from(QualityStandard)
                .where(QualityStandard.quality_type.in_(APPROVED_QUALITY_TYPES))
            )
            or 0
        ),
        "pass_measurements": judgements.count("PASS"),
        "fail_measurements": judgements.count("FAIL"),
        "no_standard_measurements": judgements.count("NO_STANDARD"),
        "measurements_by_type": by_type,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


@router.get("/analytics", response_model=QualityAnalytics)
def quality_analytics(
    quality_type: str = "ORANGE_PEEL",
    metric_code: str | None = None,
    measurement_point_id: str | None = None,
    limit: int = 500,
    db: Session = Depends(get_db),
) -> dict:
    try:
        require_approved_quality_type(quality_type)
        if metric_code:
            require_approved_metric(quality_type, metric_code)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    metric_definition = db.scalar(
        select(QualityMetricDefinition)
        .where(
            QualityMetricDefinition.quality_type == quality_type,
            *(
                [QualityMetricDefinition.code == metric_code]
                if metric_code
                else [QualityMetricDefinition.is_primary.is_(True)]
            ),
        )
        .order_by(QualityMetricDefinition.display_order)
    )
    if not metric_definition and not metric_code:
        metric_definition = db.scalar(
            select(QualityMetricDefinition)
            .where(QualityMetricDefinition.quality_type == quality_type)
            .order_by(QualityMetricDefinition.display_order)
        )
    resolved_metric_code = metric_code or (metric_definition.code if metric_definition else "")
    if not resolved_metric_code:
        raise HTTPException(status_code=404, detail="当前质量类型没有可分析指标")

    measurement_query = (
        select(QualityMeasurement)
        .where(QualityMeasurement.quality_type == quality_type)
        .order_by(QualityMeasurement.measured_at.desc())
        .limit(min(max(limit, 1), 2000))
    )
    if measurement_point_id:
        measurement_query = measurement_query.where(
            QualityMeasurement.measurement_point_id == measurement_point_id
        )
    all_measurements = list(db.scalars(measurement_query))
    selected_measurements = [item for item in all_measurements if item.is_valid]
    point_ids = {item.measurement_point_id for item in selected_measurements}
    points = {
        point.id: point
        for point in db.scalars(select(MeasurementPoint).where(MeasurementPoint.id.in_(point_ids)))
    } if point_ids else {}

    series: list[dict] = []
    no_standard_count = 0
    for measurement in selected_measurements:
        metrics = list(
            db.scalars(
                select(QualityMetricValue).where(
                    QualityMetricValue.measurement_id == measurement.id
                )
            )
        )
        metric = next((item for item in metrics if item.metric_code == resolved_metric_code), None)
        if not metric:
            continue
        evaluation = evaluate_quality_measurement(db, measurement, metrics)
        metric_result = next(
            (
                item
                for item in evaluation["metric_results"]
                if item["metric_code"] == resolved_metric_code
            ),
            None,
        )
        judgement = metric_result["judgement"] if metric_result else "NO_STANDARD"
        if judgement == "NO_STANDARD":
            no_standard_count += 1
        point = points[measurement.measurement_point_id]
        series.append(
            {
                "measurement_id": measurement.id,
                "data_no": measurement.data_no,
                "measurement_point_id": point.id,
                "measurement_point_code": point.code,
                "measurement_point_name": point.name,
                "measured_at": measurement.measured_at,
                "value": (
                    metric.corrected_value
                    if metric.corrected_value is not None
                    else metric.raw_value
                ),
                "judgement": judgement,
                "standard_min": metric_result.get("min_value") if metric_result else None,
                "standard_max": metric_result.get("max_value") if metric_result else None,
            }
        )
    series.sort(key=lambda item: item["measured_at"])
    values = [item["value"] for item in series]
    average = mean(values) if values else None
    sigma = pstdev(values) if len(values) > 1 else 0.0 if values else None
    ucl = average + 3 * sigma if average is not None and sigma is not None else None
    lcl = average - 3 * sigma if average is not None and sigma is not None else None
    out_of_control_count = (
        sum(value < lcl or value > ucl for value in values)
        if lcl is not None and ucl is not None
        else 0
    )
    if len(values) > 1:
        x_average = (len(values) - 1) / 2
        denominator = sum((index - x_average) ** 2 for index in range(len(values)))
        trend_slope = (
            sum((index - x_average) * (value - average) for index, value in enumerate(values))
            / denominator
            if denominator
            else 0.0
        )
    else:
        trend_slope = 0.0 if values else None

    lower_bounds = {item["standard_min"] for item in series if item["standard_min"] is not None}
    upper_bounds = {item["standard_max"] for item in series if item["standard_max"] is not None}
    common_lower = next(iter(lower_bounds)) if len(lower_bounds) == 1 else None
    common_upper = next(iter(upper_bounds)) if len(upper_bounds) == 1 else None
    cp = cpk = None
    if common_lower is not None and common_upper is not None and sigma and average is not None:
        cp = (common_upper - common_lower) / (6 * sigma)
        cpk = min(common_upper - average, average - common_lower) / (3 * sigma)

    point_groups: dict[str, list[dict]] = defaultdict(list)
    for item in series:
        point_groups[item["measurement_point_id"]].append(item)
    point_risks = []
    for point_series in point_groups.values():
        failures = sum(item["judgement"] == "FAIL" for item in point_series)
        point_no_standard = sum(item["judgement"] == "NO_STANDARD" for item in point_series)
        point_out_of_control = (
            sum(item["value"] < lcl or item["value"] > ucl for item in point_series)
            if lcl is not None and ucl is not None
            else 0
        )
        sample_count = len(point_series)
        latest = point_series[-1]
        risk_score = min(
            100.0,
            _ratio(failures, sample_count) * 70
            + _ratio(point_out_of_control, sample_count) * 20
            + _ratio(point_no_standard, sample_count) * 10,
        )
        point_risks.append(
            {
                "measurement_point_id": latest["measurement_point_id"],
                "measurement_point_code": latest["measurement_point_code"],
                "measurement_point_name": latest["measurement_point_name"],
                "samples": sample_count,
                "failures": failures,
                "fail_rate": _ratio(failures, sample_count),
                "no_standard_count": point_no_standard,
                "latest_value": latest["value"],
                "latest_judgement": latest["judgement"],
                "risk_score": round(risk_score, 1),
            }
        )
    point_risks.sort(key=lambda item: (item["risk_score"], item["failures"]), reverse=True)

    valid_count = len(selected_measurements)
    series_count = len(series)
    standard_count = series_count - no_standard_count
    return {
        "quality_type": quality_type,
        "metric_code": resolved_metric_code,
        "metric_name": metric_definition.name if metric_definition else resolved_metric_code,
        "unit": metric_definition.unit if metric_definition else None,
        "statistics": {
            "samples": series_count,
            "mean": average,
            "sigma": sigma,
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "ucl": ucl,
            "lcl": lcl,
            "trend_slope": trend_slope,
            "cp": cp,
            "cpk": cpk,
            "pass_rate": _ratio(sum(item["judgement"] == "PASS" for item in series), standard_count),
            "out_of_control_count": out_of_control_count,
        },
        "data_quality": {
            "total_measurements": len(all_measurements),
            "valid_measurements": valid_count,
            "invalid_measurements": len(all_measurements) - valid_count,
            "measurements_with_metric": series_count,
            "missing_metric_count": valid_count - series_count,
            "no_standard_count": no_standard_count,
            "valid_rate": _ratio(valid_count, len(all_measurements)),
            "metric_completeness": _ratio(series_count, valid_count),
            "standard_coverage": _ratio(standard_count, series_count),
            "latest_measured_at": max((item.measured_at for item in all_measurements), default=None),
        },
        "series": series,
        "point_risks": point_risks,
    }


@router.get("/metric-definitions", response_model=list[QualityMetricDefinitionRead])
def list_quality_metric_definitions(db: Session = Depends(get_db)) -> list[QualityMetricDefinition]:
    definitions = list(
        db.scalars(
            select(QualityMetricDefinition).order_by(QualityMetricDefinition.display_order)
        )
    )
    return [
        definition
        for definition in definitions
        if (definition.quality_type, definition.code) in APPROVED_METRIC_KEYS
    ]


@router.post("/metric-definitions/seed-catalog")
def seed_quality_metric_catalog(db: Session = Depends(get_db)) -> dict:
    existing = set(
        db.execute(
            select(QualityMetricDefinition.quality_type, QualityMetricDefinition.code)
        ).all()
    )
    resources = [
        QualityMetricDefinition(**definition)
        for definition in QUALITY_METRIC_CATALOG
        if (definition["quality_type"], definition["code"]) not in existing
    ]
    db.add_all(resources)
    db.commit()
    return {
        "catalog_size": len(QUALITY_METRIC_CATALOG),
        "created": len(resources),
        "existing": len(QUALITY_METRIC_CATALOG) - len(resources),
    }


@router.get("/measurements", response_model=list[QualityMeasurementRead])
def list_quality_measurements(
    limit: int = 100,
    quality_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    query = (
        select(QualityMeasurement)
        .where(QualityMeasurement.quality_type.in_(APPROVED_QUALITY_TYPES))
        .order_by(QualityMeasurement.measured_at.desc())
    )
    if quality_type:
        try:
            require_approved_quality_type(quality_type)
        except ScopeViolation as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        query = query.where(QualityMeasurement.quality_type == quality_type)
    measurements = list(
        db.scalars(query.limit(min(max(limit, 1), 500)))
    )
    return [_measurement_result(db, measurement) for measurement in measurements]


@router.get("/measurements/{measurement_id}", response_model=QualityMeasurementRead)
def get_quality_measurement(
    measurement_id: str, db: Session = Depends(get_db)
) -> dict:
    return _measurement_result(
        db,
        _required(db, QualityMeasurement, measurement_id, "质量数据"),
    )


@router.post(
    "/measurements",
    response_model=QualityMeasurementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_quality_measurement(
    payload: QualityMeasurementCreate, db: Session = Depends(get_db)
) -> dict:
    _validate_quality_scope(
        payload.quality_type,
        [metric.metric_code for metric in payload.metrics],
    )
    if db.scalar(select(QualityMeasurement).where(QualityMeasurement.data_no == payload.data_no)):
        raise HTTPException(status_code=409, detail="质量数据编号已存在")
    if not db.get(ProductionRun, payload.production_run_id):
        raise HTTPException(status_code=404, detail="生产事件不存在")
    point = db.get(MeasurementPoint, payload.measurement_point_id)
    if not point:
        raise HTTPException(status_code=404, detail="测量点不存在")
    if payload.measurement_group_id and not db.get(MeasurementGroup, payload.measurement_group_id):
        raise HTTPException(status_code=404, detail="测量编组不存在")

    measurement_data = payload.model_dump(exclude={"metrics"})
    measurement = QualityMeasurement(**measurement_data)
    db.add(measurement)
    db.flush()
    metrics = [
        QualityMetricValue(measurement_id=measurement.id, **metric.model_dump())
        for metric in payload.metrics
    ]
    db.add_all(metrics)
    db.commit()
    db.refresh(measurement)
    for metric in metrics:
        db.refresh(metric)
    return _measurement_dict(
        measurement, metrics, point, evaluate_quality_measurement(db, measurement, metrics)
    )


@router.patch("/measurements/{measurement_id}", response_model=QualityMeasurementRead)
def update_quality_measurement(
    measurement_id: str,
    payload: QualityMeasurementUpdate,
    db: Session = Depends(get_db),
) -> dict:
    measurement = _required(db, QualityMeasurement, measurement_id, "质量数据")
    changes = payload.model_dump(exclude_unset=True)
    metrics_payload = changes.pop("metrics", None)
    resolved_quality_type = changes.get("quality_type", measurement.quality_type)
    resolved_metric_codes = (
        [metric["metric_code"] for metric in metrics_payload]
        if metrics_payload is not None
        else list(
            db.scalars(
                select(QualityMetricValue.metric_code).where(
                    QualityMetricValue.measurement_id == measurement_id
                )
            )
        )
    )
    _validate_quality_scope(resolved_quality_type, resolved_metric_codes)
    if "data_no" in changes:
        duplicate = db.scalar(
            select(QualityMeasurement).where(
                QualityMeasurement.data_no == changes["data_no"],
                QualityMeasurement.id != measurement_id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="质量数据编号已存在")
    if "production_run_id" in changes:
        _required(db, ProductionRun, changes["production_run_id"], "生产事件")
    if "measurement_point_id" in changes:
        _required(db, MeasurementPoint, changes["measurement_point_id"], "测量点")
    if changes.get("measurement_group_id"):
        _required(db, MeasurementGroup, changes["measurement_group_id"], "测量编组")
    for field, value in changes.items():
        setattr(measurement, field, value)
    if metrics_payload is not None:
        db.execute(delete(QualityMetricValue).where(QualityMetricValue.measurement_id == measurement_id))
        db.add_all(
            [
                QualityMetricValue(measurement_id=measurement_id, **metric)
                for metric in metrics_payload
            ]
        )
    db.commit()
    db.refresh(measurement)
    return _measurement_result(db, measurement)


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quality_measurement(
    measurement_id: str, db: Session = Depends(get_db)
) -> Response:
    measurement = _required(db, QualityMeasurement, measurement_id, "质量数据")
    try:
        db.execute(delete(QualityMetricValue).where(QualityMetricValue.measurement_id == measurement_id))
        db.delete(measurement)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="质量数据已被模型快照或闭环复测引用，不能删除",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/standards", response_model=list[QualityStandardRead])
def list_quality_standards(db: Session = Depends(get_db)) -> list[QualityStandard]:
    return list(
        db.scalars(
            select(QualityStandard)
            .where(QualityStandard.quality_type.in_(APPROVED_QUALITY_TYPES))
            .order_by(QualityStandard.standard_no)
        )
    )


@router.get("/standards/{standard_id}", response_model=QualityStandardRead)
def get_quality_standard(
    standard_id: str, db: Session = Depends(get_db)
) -> QualityStandard:
    return _required(db, QualityStandard, standard_id, "质量标准")


@router.post(
    "/standards",
    response_model=QualityStandardRead,
    status_code=status.HTTP_201_CREATED,
)
def create_quality_standard(
    payload: QualityStandardCreate, db: Session = Depends(get_db)
) -> QualityStandard:
    _validate_standard_relations(db, payload.model_dump())
    standard = QualityStandard(**payload.model_dump())
    db.add(standard)
    db.commit()
    db.refresh(standard)
    return standard


def _validate_standard_relations(db: Session, values: dict) -> None:
    _validate_quality_scope(values["quality_type"], [values["metric_code"]])
    for field, model, label in (
        ("vehicle_model_id", VehicleModel, "车型"),
        ("color_id", Color, "颜色"),
        ("part_id", Part, "零件"),
        ("measurement_point_id", MeasurementPoint, "测量点"),
    ):
        if values.get(field):
            _required(db, model, values[field], label)
    minimum = values.get("min_value")
    maximum = values.get("max_value")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise HTTPException(status_code=422, detail="质量标准下限不能大于上限")


@router.patch("/standards/{standard_id}", response_model=QualityStandardRead)
def update_quality_standard(
    standard_id: str,
    payload: QualityStandardUpdate,
    db: Session = Depends(get_db),
) -> QualityStandard:
    standard = _required(db, QualityStandard, standard_id, "质量标准")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "quality_type": standard.quality_type,
        "metric_code": standard.metric_code,
        "vehicle_model_id": standard.vehicle_model_id,
        "color_id": standard.color_id,
        "part_id": standard.part_id,
        "measurement_point_id": standard.measurement_point_id,
        "min_value": standard.min_value,
        "max_value": standard.max_value,
        **changes,
    }
    _validate_standard_relations(db, merged)
    for field, value in changes.items():
        setattr(standard, field, value)
    db.commit()
    db.refresh(standard)
    return standard


@router.delete("/standards/{standard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quality_standard(
    standard_id: str, db: Session = Depends(get_db)
) -> Response:
    standard = _required(db, QualityStandard, standard_id, "质量标准")
    db.delete(standard)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
