"""Measurement reliability classifier.

Day-1 factory policy (PQ-AI): instruments are a ledger with enable/disable only.
Method / calibration / reference / import-profile / repeats remain optional
lineage columns in the schema, but they do not gate upload, judgement, training,
or closed-loop verification. Complex provenance can be re-enabled later without
DDL by tightening this classifier.
"""

from sqlalchemy.orm import Session

from app.models.domain import MeasurementInstrument, QualityMeasurement


VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
FAILED = "FAILED"


def assess_measurement_reliability(
    db: Session,
    measurement: QualityMeasurement,
) -> tuple[str, list[str]]:
    """Lean gate: manual validity + optional instrument ACTIVE/type match."""
    failures: list[str] = []

    if not measurement.is_valid:
        failures.append("质量数据被人工标记为无效")
        return FAILED, failures

    if measurement.instrument_id:
        instrument = db.get(MeasurementInstrument, measurement.instrument_id)
        if not instrument:
            failures.append("关联的测量仪器不存在或已归档")
        else:
            if instrument.status != "ACTIVE":
                failures.append(f"测量仪器已停用（{instrument.status}）")
            supported = list(instrument.supported_quality_types or [])
            if supported and measurement.quality_type not in supported:
                failures.append("测量仪器不支持当前质量类型")
            if (
                measurement.device_code
                and instrument.code
                and measurement.device_code != instrument.code
            ):
                failures.append("设备代码与仪器台账不一致")

    if failures:
        return FAILED, failures
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
