from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    MeasurementCalibrationRecord,
    MeasurementImportProfile,
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementReferenceStandard,
    MeasurementRepeatReading,
    QualityMeasurement,
    QualityMetricValue,
)


VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
FAILED = "FAILED"


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def assess_measurement_reliability(
    db: Session,
    measurement: QualityMeasurement,
) -> tuple[str, list[str]]:
    missing: list[str] = []
    failures: list[str] = []
    if not measurement.is_valid:
        failures.append("质量数据被人工标记为无效")

    instrument = (
        db.get(MeasurementInstrument, measurement.instrument_id)
        if measurement.instrument_id
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

    if not instrument:
        missing.append("缺少受治理测量仪器")
    else:
        if instrument.status != "ACTIVE":
            failures.append(f"测量仪器状态为 {instrument.status}")
        if measurement.quality_type not in instrument.supported_quality_types:
            failures.append("测量仪器不支持当前质量类型")
        if measurement.device_code and measurement.device_code != instrument.code:
            failures.append("设备代码与受治理仪器不一致")

    if not method:
        missing.append("缺少受治理测量方法")
    else:
        if not method.is_active:
            failures.append("测量方法已停用")
        if method.quality_type != measurement.quality_type:
            failures.append("测量方法与质量类型不匹配")
        if instrument and method.instrument_type != instrument.instrument_type:
            failures.append("测量方法与仪器类型不匹配")
        if method.requires_direction and not measurement.measurement_direction:
            missing.append("测量方法要求记录测量方向")

    if instrument and instrument.calibration_required:
        if not calibration:
            missing.append("缺少有效校准/检查记录")
        else:
            if calibration.instrument_id != instrument.id:
                failures.append("校准记录不属于当前仪器")
            if calibration.method_id and method and calibration.method_id != method.id:
                failures.append("校准记录与测量方法不匹配")
            if calibration.result != "PASS":
                failures.append(f"校准/检查结果为 {calibration.result}")
            measured_at = _utc(measurement.measured_at)
            if measured_at < _utc(calibration.calibrated_at):
                failures.append("测量时间早于校准/检查时间")
            if measured_at > _utc(calibration.valid_until):
                failures.append("测量时校准/检查记录已过期")

    if method and method.requires_reference:
        if not reference:
            missing.append("测量方法要求关联参考件/数字标准")
        else:
            if reference.status != "ACTIVE":
                failures.append(f"参考件状态为 {reference.status}")
            if reference.quality_type != measurement.quality_type:
                failures.append("参考件与质量类型不匹配")
            measured_at = _utc(measurement.measured_at)
            if reference.valid_from and measured_at < _utc(reference.valid_from):
                failures.append("测量时间早于参考件有效期")
            if reference.valid_until and measured_at > _utc(reference.valid_until):
                failures.append("测量时参考件已过期")

    if measurement.raw_file_uri and not import_profile:
        missing.append("设备原始文件缺少版本化导入模板")
    if import_profile:
        if not import_profile.is_active:
            failures.append("导入模板已停用")
        if import_profile.quality_type != measurement.quality_type:
            failures.append("导入模板与质量类型不匹配")
        if instrument and import_profile.instrument_type != instrument.instrument_type:
            failures.append("导入模板与仪器类型不匹配")

    repeats = list(
        db.scalars(
            select(MeasurementRepeatReading).where(
                MeasurementRepeatReading.measurement_id == measurement.id,
                MeasurementRepeatReading.is_valid.is_(True),
            )
        )
    )
    metric_codes = set(
        db.scalars(
            select(QualityMetricValue.metric_code).where(
                QualityMetricValue.measurement_id == measurement.id
            )
        )
    )
    if measurement.quality_type == "THICKNESS":
        layer_metrics = metric_codes - {"thickness_total"}
        if layer_metrics and (not method or not method.layer_scope or method.layer_scope == "TOTAL_FILM"):
            failures.append(
                "单层/单遍膜厚必须关联明确记录该层测量或推断方法的 layer_scope"
            )
    ambiguous_effect_metrics = {
        "dst",
        "ds",
        "dg",
        "ds15",
        "ds45",
        "ds75",
        "dsi15",
        "dsi45",
        "dsi75",
        "dsa15",
        "dsa45",
        "dsa75",
    }
    if measurement.quality_type == "COLOR_DIFFERENCE" and metric_codes & ambiguous_effect_metrics:
        if not import_profile:
            missing.append("色差效应指标必须关联版本化导入模板以确认字段语义")
    minimum_repeats = method.minimum_repeats if method else 1
    for metric_code in metric_codes:
        repeat_count = len(
            {reading.repeat_no for reading in repeats if reading.metric_code == metric_code}
        )
        if repeat_count < minimum_repeats:
            missing.append(
                f"指标 {metric_code} 有效重复读数不足：需要 {minimum_repeats}，当前 {repeat_count}"
            )

    if failures:
        return FAILED, failures + missing
    if missing:
        return UNVERIFIED, missing
    return VERIFIED, []


def refresh_measurement_reliability(
    db: Session,
    measurement: QualityMeasurement,
) -> tuple[str, list[str]]:
    status, issues = assess_measurement_reliability(db, measurement)
    measurement.reliability_status = status
    measurement.reliability_issues = issues
    return status, issues


def measurement_is_eligible(measurement: QualityMeasurement) -> bool:
    return measurement.is_valid and measurement.reliability_status == VERIFIED
