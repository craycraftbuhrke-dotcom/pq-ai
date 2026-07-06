from collections import defaultdict
from csv import DictReader
from datetime import datetime
from io import StringIO
from statistics import mean, pstdev

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.delete_policy import reject_physical_delete
from app.core.referential_integrity import check_fk
from app.db.session import get_db
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
    MeasurementCalibrationRecord,
    MeasurementGroup,
    MeasurementImportProfile,
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementPoint,
    MeasurementProbe,
    MeasurementReferenceStandard,
    MeasurementRepeatReading,
    Part,
    ProductionRun,
    QualityMeasurement,
    QualityMetricDefinition,
    QualityMetricValue,
    QualityStandard,
    VehicleModel,
)
from app.services.catalog_seed import seed_quality_metric_catalog
from app.services.measurement_reliability import measurement_is_eligible
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
from app.services.measurement_reliability import (
    FAILED,
    UNVERIFIED,
    VERIFIED,
    refresh_measurement_reliability,
)
from app.services.quality_evaluation import evaluate_quality_measurement

router = APIRouter(prefix="/quality", tags=["quality-data"])


def _validate_quality_scope(quality_type: str, metric_codes: list[str]) -> None:
    try:
        require_approved_metrics(quality_type, metric_codes)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _validate_repeat_readings(quality_type: str, repeat_readings: list[dict]) -> None:
    _validate_quality_scope(
        quality_type,
        [str(reading["metric_code"]) for reading in repeat_readings],
    )
    keys = [
        (int(reading["repeat_no"]), str(reading["metric_code"]))
        for reading in repeat_readings
    ]
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=422, detail="逐次读数的重复序号与指标代码不能重复")


def _validate_measurement_governance_relations(db: Session, values: dict) -> None:
    for field, model, label in (
        ("instrument_id", MeasurementInstrument, "测量仪器"),
        ("measurement_probe_id", MeasurementProbe, "测量探头"),
        ("measurement_method_id", MeasurementMethod, "测量方法"),
        ("calibration_record_id", MeasurementCalibrationRecord, "校准/检查记录"),
        ("reference_standard_id", MeasurementReferenceStandard, "参考件"),
        ("import_profile_id", MeasurementImportProfile, "导入模板"),
    ):
        if values.get(field):
            _required(db, model, values[field], label)
    if values.get("measurement_probe_id") and not values.get("instrument_id"):
        raise HTTPException(status_code=422, detail="维护测量探头时必须同时关联测量仪器")
    if values.get("measurement_probe_id") and values.get("instrument_id"):
        probe = _required(db, MeasurementProbe, values["measurement_probe_id"], "测量探头")
        if probe.instrument_id != values["instrument_id"]:
            raise HTTPException(status_code=422, detail="测量探头不属于该测量仪器")


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _measurement_dict(
    db: Session,
    measurement: QualityMeasurement,
    metrics: list[QualityMetricValue],
    point: MeasurementPoint,
    evaluation: dict,
) -> dict:
    instrument = (
        db.get(MeasurementInstrument, measurement.instrument_id)
        if measurement.instrument_id
        else None
    )
    probe = (
        db.get(MeasurementProbe, measurement.measurement_probe_id)
        if measurement.measurement_probe_id
        else None
    )
    method = (
        db.get(MeasurementMethod, measurement.measurement_method_id)
        if measurement.measurement_method_id
        else None
    )
    calibration = (
        db.get(MeasurementCalibrationRecord, measurement.calibration_record_id)
        if measurement.calibration_record_id
        else None
    )
    reference = (
        db.get(MeasurementReferenceStandard, measurement.reference_standard_id)
        if measurement.reference_standard_id
        else None
    )
    import_profile = (
        db.get(MeasurementImportProfile, measurement.import_profile_id)
        if measurement.import_profile_id
        else None
    )
    repeat_readings = list(
        db.scalars(
            select(MeasurementRepeatReading)
            .where(MeasurementRepeatReading.measurement_id == measurement.id)
            .order_by(MeasurementRepeatReading.repeat_no, MeasurementRepeatReading.metric_code)
        )
    )
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
        "instrument_id": measurement.instrument_id,
        "instrument_code": instrument.code if instrument else None,
        "instrument_name": instrument.name if instrument else None,
        "measurement_probe_id": measurement.measurement_probe_id,
        "measurement_probe_code": probe.code if probe else None,
        "measurement_probe_name": probe.name if probe else None,
        "measurement_method_id": measurement.measurement_method_id,
        "measurement_method_code": method.code if method else None,
        "calibration_record_id": measurement.calibration_record_id,
        "calibration_no": calibration.calibration_no if calibration else None,
        "reference_standard_id": measurement.reference_standard_id,
        "reference_standard_code": reference.code if reference else None,
        "import_profile_id": measurement.import_profile_id,
        "import_profile_code": (
            f"{import_profile.code}:{import_profile.version}" if import_profile else None
        ),
        "measurement_direction": measurement.measurement_direction,
        "raw_file_uri": measurement.raw_file_uri,
        "reliability_status": measurement.reliability_status,
        "reliability_issues": measurement.reliability_issues or [],
        "status_score": measurement.status_score,
        "is_valid": measurement.is_valid,
        "judgement": evaluation["judgement"],
        "violations": evaluation["violations"],
        "metrics": metrics,
        "repeat_readings": repeat_readings,
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
        db,
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
                    QualityMeasurement.reliability_status == VERIFIED,
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
        "verified_measurements": sum(
            measurement.reliability_status == VERIFIED for measurement in measurements
        ),
        "unverified_measurements": sum(
            measurement.reliability_status == UNVERIFIED for measurement in measurements
        ),
        "failed_reliability_measurements": sum(
            measurement.reliability_status == FAILED for measurement in measurements
        ),
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
    selected_measurements = [
        item
        for item in all_measurements
        if item.is_valid and item.reliability_status == VERIFIED
    ]
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
def seed_quality_metric_catalog_endpoint(db: Session = Depends(get_db)) -> dict:
    return seed_quality_metric_catalog(db)


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
    _validate_repeat_readings(
        payload.quality_type,
        [reading.model_dump() for reading in payload.repeat_readings],
    )
    _validate_measurement_governance_relations(db, payload.model_dump())
    check_fk(db, ProductionRun, payload.production_run_id, "生产事件")
    check_fk(db, MeasurementPoint, payload.measurement_point_id, "测量点")
    if db.scalar(select(QualityMeasurement).where(QualityMeasurement.data_no == payload.data_no)):
        raise HTTPException(status_code=409, detail="质量数据编号已存在")
    if not db.get(ProductionRun, payload.production_run_id):
        raise HTTPException(status_code=404, detail="生产事件不存在")
    point = db.get(MeasurementPoint, payload.measurement_point_id)
    if not point:
        raise HTTPException(status_code=404, detail="测量点不存在")
    if payload.measurement_group_id and not db.get(MeasurementGroup, payload.measurement_group_id):
        raise HTTPException(status_code=404, detail="测量编组不存在")

    measurement_data = payload.model_dump(exclude={"metrics", "repeat_readings"})
    if payload.instrument_id and not measurement_data.get("device_code"):
        measurement_data["device_code"] = db.get(MeasurementInstrument, payload.instrument_id).code
    measurement = QualityMeasurement(**measurement_data)
    db.add(measurement)
    db.flush()
    metrics = [
        QualityMetricValue(measurement_id=measurement.id, **metric.model_dump())
        for metric in payload.metrics
    ]
    db.add_all(metrics)
    db.add_all(
        [
            MeasurementRepeatReading(
                measurement_id=measurement.id,
                **reading.model_dump(),
            )
            for reading in payload.repeat_readings
        ]
    )
    db.flush()
    refresh_measurement_reliability(db, measurement)
    db.commit()
    return _measurement_result(db, measurement)


@router.patch("/measurements/{measurement_id}", response_model=QualityMeasurementRead)
def update_quality_measurement(
    measurement_id: str,
    payload: QualityMeasurementUpdate,
    db: Session = Depends(get_db),
) -> dict:
    measurement = _required(db, QualityMeasurement, measurement_id, "质量数据")
    changes = payload.model_dump(exclude_unset=True)
    metrics_payload = changes.pop("metrics", None)
    repeat_readings_payload = changes.pop("repeat_readings", None)
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
    if repeat_readings_payload is not None:
        _validate_repeat_readings(resolved_quality_type, repeat_readings_payload)
    _validate_measurement_governance_relations(
        db,
        {
            "instrument_id": changes.get("instrument_id", measurement.instrument_id),
            "measurement_probe_id": changes.get(
                "measurement_probe_id",
                measurement.measurement_probe_id,
            ),
            "measurement_method_id": changes.get(
                "measurement_method_id",
                measurement.measurement_method_id,
            ),
            "calibration_record_id": changes.get(
                "calibration_record_id",
                measurement.calibration_record_id,
            ),
            "reference_standard_id": changes.get(
                "reference_standard_id",
                measurement.reference_standard_id,
            ),
            "import_profile_id": changes.get("import_profile_id", measurement.import_profile_id),
        },
    )
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
    if changes.get("instrument_id") and "device_code" not in changes:
        changes["device_code"] = db.get(MeasurementInstrument, changes["instrument_id"]).code
    for field, value in changes.items():
        setattr(measurement, field, value)
    if metrics_payload is not None:
        existing_metrics = {
            metric.metric_code: metric
            for metric in db.scalars(
                select(QualityMetricValue).where(
                    QualityMetricValue.measurement_id == measurement_id
                )
            )
        }
        for metric in metrics_payload:
            existing = existing_metrics.get(metric["metric_code"])
            if existing:
                for field, value in metric.items():
                    setattr(existing, field, value)
            else:
                db.add(QualityMetricValue(measurement_id=measurement_id, **metric))
    if repeat_readings_payload is not None:
        existing_readings = {
            (reading.repeat_no, reading.metric_code): reading
            for reading in db.scalars(
                select(MeasurementRepeatReading).where(
                    MeasurementRepeatReading.measurement_id == measurement_id
                )
            )
        }
        for reading in repeat_readings_payload:
            key = (reading["repeat_no"], reading["metric_code"])
            existing = existing_readings.get(key)
            if existing:
                for field, value in reading.items():
                    setattr(existing, field, value)
            else:
                db.add(MeasurementRepeatReading(measurement_id=measurement_id, **reading))
    db.flush()
    refresh_measurement_reliability(db, measurement)
    db.commit()
    db.refresh(measurement)
    return _measurement_result(db, measurement)


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quality_measurement(
    measurement_id: str, db: Session = Depends(get_db)
) -> Response:
    _required(db, QualityMeasurement, measurement_id, "质量数据")
    reject_physical_delete("质量数据")


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
    check_fk(db, VehicleModel, values.get("vehicle_model_id"), "车型")
    check_fk(db, Color, values.get("color_id"), "颜色")
    check_fk(db, Part, values.get("part_id"), "零件")
    check_fk(db, MeasurementPoint, values.get("measurement_point_id"), "测量点")
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
    _required(db, QualityStandard, standard_id, "质量标准")
    reject_physical_delete("质量标准")

@router.get("/monitoring/quality-summary")
def data_quality_monitoring(db: Session = Depends(get_db)) -> dict:
    total_measurements = int(db.scalar(select(func.count()).select_from(QualityMeasurement)) or 0)
    valid_measurements = int(db.scalar(select(func.count()).select_from(QualityMeasurement).where(QualityMeasurement.is_valid.is_(True))) or 0)
    verified_measurements = int(db.scalar(select(func.count()).select_from(QualityMeasurement).where(QualityMeasurement.reliability_status == "VERIFIED")) or 0)
    unverified_measurements = int(db.scalar(select(func.count()).select_from(QualityMeasurement).where(QualityMeasurement.reliability_status == "UNVERIFIED")) or 0)
    failed_measurements = int(db.scalar(select(func.count()).select_from(QualityMeasurement).where(QualityMeasurement.reliability_status == "FAILED")) or 0)

    total_instruments = int(db.scalar(select(func.count()).select_from(MeasurementInstrument)) or 0)
    active_instruments = int(db.scalar(select(func.count()).select_from(MeasurementInstrument).where(MeasurementInstrument.status == "ACTIVE")) or 0)

    now = datetime.now()
    valid_calibrations = int(db.scalar(select(func.count()).select_from(MeasurementCalibrationRecord).where(MeasurementCalibrationRecord.result == "PASS", MeasurementCalibrationRecord.valid_until > now)) or 0)
    expired_calibrations = int(db.scalar(select(func.count()).select_from(MeasurementCalibrationRecord).where(MeasurementCalibrationRecord.valid_until <= now)) or 0)
    total_calibrations = int(db.scalar(select(func.count()).select_from(MeasurementCalibrationRecord)) or 0)

    total_standards = int(db.scalar(select(func.count()).select_from(QualityStandard).where(QualityStandard.is_active.is_(True))) or 0)

    metric_completeness = round(valid_measurements / max(total_measurements, 1) * 100, 1)
    verification_rate = round(verified_measurements / max(valid_measurements, 1) * 100, 1)
    calibration_health = round(valid_calibrations / max(total_calibrations, 1) * 100, 1) if total_calibrations else 0

    reliability_by_type = [
        {
            "quality_type": quality_type,
            "total": int(db.scalar(select(func.count()).select_from(QualityMeasurement).where(QualityMeasurement.quality_type == quality_type)) or 0),
            "verified": int(db.scalar(select(func.count()).select_from(QualityMeasurement).where(QualityMeasurement.quality_type == quality_type, QualityMeasurement.reliability_status == "VERIFIED")) or 0),
            "failed": int(db.scalar(select(func.count()).select_from(QualityMeasurement).where(QualityMeasurement.quality_type == quality_type, QualityMeasurement.reliability_status == "FAILED")) or 0),
        }
        for quality_type in ("ORANGE_PEEL", "COLOR_DIFFERENCE", "THICKNESS")
    ]

    instruments_requiring_calibration = [
        {
            "id": instrument.id,
            "code": instrument.code,
            "name": instrument.name,
            "instrument_type": instrument.instrument_type,
            "status": instrument.status,
        }
        for instrument in db.scalars(
            select(MeasurementInstrument).where(
                MeasurementInstrument.calibration_required.is_(True),
                MeasurementInstrument.status == "ACTIVE",
            )
        ).all()
        if not db.scalar(
            select(MeasurementCalibrationRecord).where(
                MeasurementCalibrationRecord.instrument_id == instrument.id,
                MeasurementCalibrationRecord.result == "PASS",
                MeasurementCalibrationRecord.valid_until > now,
            )
        )
    ]

    return {
        "overview": {
            "total_measurements": total_measurements,
            "valid_measurements": valid_measurements,
            "verified_measurements": verified_measurements,
            "unverified_measurements": unverified_measurements,
            "failed_measurements": failed_measurements,
            "metric_completeness": metric_completeness,
            "verification_rate": verification_rate,
        },
        "instruments": {
            "total": total_instruments,
            "active": active_instruments,
            "total_calibrations": total_calibrations,
            "valid_calibrations": valid_calibrations,
            "expired_calibrations": expired_calibrations,
            "calibration_health": calibration_health,
            "needs_calibration": instruments_requiring_calibration,
        },
        "standards": {
            "active_standards": total_standards,
        },
        "reliability_by_type": reliability_by_type,
        "health_score": round(
            (metric_completeness * 0.3 + verification_rate * 0.3 + calibration_health * 0.4),
            1,
        ),
    }


@router.post("/measurements/import-csv")
def import_quality_csv(file: UploadFile, db: Session = Depends(get_db)) -> dict:
    content = (file.file.read()).decode("utf-8-sig")
    reader = DictReader(StringIO(content))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV 文件为空或缺少表头")
    required = {"data_no", "production_run_no", "measurement_point_code", "quality_type", "measured_at"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise HTTPException(status_code=422, detail=f"缺少必填列：{', '.join(sorted(missing))}")

    result = {"total_rows": 0, "created": 0, "updated": 0, "skipped": 0, "errors": []}
    run_by_no = {
        run.run_no: run
        for run in db.scalars(select(ProductionRun)).all()
    }
    point_by_code = {
        point.code: point
        for point in db.scalars(select(MeasurementPoint)).all()
    }

    for row_num, row in enumerate(reader, start=2):
        result["total_rows"] += 1
        try:
            data_no = (row.get("data_no") or "").strip()
            run_no = (row.get("production_run_no") or "").strip()
            point_code = (row.get("measurement_point_code") or "").strip()
            quality_type = (row.get("quality_type") or "").strip().upper()
            measured_at_str = (row.get("measured_at") or "").strip()
            measured_by = (row.get("measured_by") or "").strip() or None
            data_type = (row.get("data_type") or "TEST").strip()
            metric_codes_str = (row.get("metric_codes") or "").strip()
            metric_values_str = (row.get("metric_values") or "").strip()
            metric_units_str = (row.get("metric_units") or "").strip()

            if not all([data_no, run_no, point_code, quality_type, measured_at_str]):
                result["errors"].append(f"第{row_num}行：必填字段缺失")
                result["skipped"] += 1
                continue

            if quality_type not in APPROVED_QUALITY_TYPES:
                result["errors"].append(f"第{row_num}行：质量类型 {quality_type} 不在批准范围")
                result["skipped"] += 1
                continue

            run = run_by_no.get(run_no)
            if not run:
                result["errors"].append(f"第{row_num}行：生产事件 {run_no} 不存在")
                result["skipped"] += 1
                continue

            point = point_by_code.get(point_code)
            if not point:
                result["errors"].append(f"第{row_num}行：测量点 {point_code} 不存在")
                result["skipped"] += 1
                continue

            try:
                measured_at = datetime.fromisoformat(measured_at_str)
            except ValueError:
                result["errors"].append(f"第{row_num}行：测量时间格式无效，需为 ISO 8601 格式")
                result["skipped"] += 1
                continue

            existing = db.scalar(select(QualityMeasurement).where(QualityMeasurement.data_no == data_no))
            if existing:
                existing.quality_type = quality_type
                existing.measured_at = measured_at
                existing.measured_by = measured_by or existing.measured_by
                existing.data_type = data_type
                db.flush()
                result["updated"] += 1
                measurement = existing
            else:
                measurement = QualityMeasurement(
                    data_no=data_no,
                    production_run_id=run.id,
                    measurement_point_id=point.id,
                    quality_type=quality_type,
                    data_type=data_type,
                    measured_at=measured_at,
                    measured_by=measured_by,
                )
                db.add(measurement)
                db.flush()
                result["created"] += 1

            metric_codes = [c.strip() for c in metric_codes_str.split(",") if c.strip()]
            metric_values = metric_values_str.split(",") if metric_values_str else []
            metric_units = [u.strip() for u in metric_units_str.split(",")] if metric_units_str else []

            if metric_codes:
                for i, code in enumerate(metric_codes):
                    if i >= len(metric_values):
                        break
                    try:
                        value = float(metric_values[i].strip())
                    except (ValueError, IndexError):
                        result["errors"].append(f"第{row_num}行：指标 {code} 的值无效")
                        continue
                    unit = metric_units[i].strip() if i < len(metric_units) else None
                    existing_metric = db.scalar(
                        select(QualityMetricValue).where(
                            QualityMetricValue.measurement_id == measurement.id,
                            QualityMetricValue.metric_code == code,
                        )
                    )
                    if existing_metric:
                        existing_metric.raw_value = value
                        if unit:
                            existing_metric.unit = unit
                    else:
                        db.add(
                            QualityMetricValue(
                                measurement_id=measurement.id,
                                metric_code=code,
                                metric_name=code,
                                raw_value=value,
                                unit=unit or None,
                            )
                        )
            db.commit()
        except Exception as exc:
            db.rollback()
            result["errors"].append(f"第{row_num}行：处理异常 - {exc}")
            result["skipped"] += 1

    return result
