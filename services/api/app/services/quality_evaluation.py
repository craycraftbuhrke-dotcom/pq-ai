from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    MeasurementPoint,
    ProductionRun,
    QualityMeasurement,
    QualityMetricValue,
    QualityStandard,
)


def evaluate_quality_measurement(
    db: Session,
    measurement: QualityMeasurement,
    metrics: list[QualityMetricValue],
) -> dict:
    if not measurement.is_valid:
        return {"judgement": "INVALID", "violations": ["质量数据被标记为无效"], "metric_results": []}
    if measurement.reliability_status != "VERIFIED":
        issues = measurement.reliability_issues or ["测量可靠性尚未验证"]
        return {
            "judgement": "INVALID",
            "violations": issues,
            "metric_results": [],
        }

    production_run = db.get(ProductionRun, measurement.production_run_id)
    point = db.get(MeasurementPoint, measurement.measurement_point_id)
    if not production_run or not point:
        return {
            "judgement": "NO_STANDARD",
            "violations": ["缺少生产事件或测量点上下文"],
            "metric_results": [],
        }

    metric_codes = [metric.metric_code for metric in metrics]
    standards = list(
        db.scalars(
            select(QualityStandard).where(
                QualityStandard.is_active.is_(True),
                QualityStandard.quality_type == measurement.quality_type,
                QualityStandard.metric_code.in_(metric_codes),
            )
        )
    )
    violations: list[str] = []
    metric_results: list[dict] = []
    matched_count = 0
    for metric in metrics:
        candidates = [
            standard
            for standard in standards
            if standard.metric_code == metric.metric_code
            and (standard.vehicle_model_id is None or standard.vehicle_model_id == production_run.vehicle_model_id)
            and (standard.color_id is None or standard.color_id == production_run.color_id)
            and (standard.part_id is None or standard.part_id == point.part_id)
            and (
                standard.measurement_point_id is None
                or standard.measurement_point_id == measurement.measurement_point_id
            )
        ]
        candidates.sort(
            key=lambda standard: sum(
                value is not None
                for value in (
                    standard.vehicle_model_id,
                    standard.color_id,
                    standard.part_id,
                    standard.measurement_point_id,
                )
            ),
            reverse=True,
        )
        standard = candidates[0] if candidates else None
        value = metric.corrected_value if metric.corrected_value is not None else metric.raw_value
        if not standard:
            metric_results.append(
                {
                    "metric_code": metric.metric_code,
                    "value": value,
                    "judgement": "NO_STANDARD",
                    "standard_no": None,
                }
            )
            continue

        matched_count += 1
        passed = (standard.min_value is None or value >= standard.min_value) and (
            standard.max_value is None or value <= standard.max_value
        )
        metric_results.append(
            {
                "metric_code": metric.metric_code,
                "value": value,
                "judgement": "PASS" if passed else "FAIL",
                "standard_no": standard.standard_no,
                "min_value": standard.min_value,
                "max_value": standard.max_value,
            }
        )
        if not passed:
            lower = f"≥ {standard.min_value}" if standard.min_value is not None else None
            upper = f"≤ {standard.max_value}" if standard.max_value is not None else None
            requirement = " 且 ".join(item for item in (lower, upper) if item)
            violations.append(f"{metric.metric_name} {value:g}，要求 {requirement}")

    if violations:
        judgement = "FAIL"
    elif matched_count:
        judgement = "PASS"
    else:
        judgement = "NO_STANDARD"
    return {
        "judgement": judgement,
        "violations": violations,
        "metric_results": metric_results,
    }
