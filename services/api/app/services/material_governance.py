from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.domain import (
    MaterialBatch,
    MaterialBatchTestResult,
    MaterialCharacteristicDefinition,
    MaterialSpecification,
    MaterialTestMethod,
)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def matching_active_specification(
    db: Session,
    batch: MaterialBatch,
    characteristic_id: str,
    method_id: str,
    tested_at: datetime,
) -> MaterialSpecification | None:
    tested = _utc(tested_at)
    candidates = list(
        db.scalars(
            select(MaterialSpecification)
            .where(
                MaterialSpecification.material_code == batch.material_code,
                MaterialSpecification.characteristic_definition_id == characteristic_id,
                MaterialSpecification.method_id == method_id,
                MaterialSpecification.status == "ACTIVE",
                or_(
                    MaterialSpecification.effective_from.is_(None),
                    MaterialSpecification.effective_from <= tested,
                ),
                or_(
                    MaterialSpecification.effective_to.is_(None),
                    MaterialSpecification.effective_to >= tested,
                ),
            )
            .order_by(MaterialSpecification.approved_at.desc())
        )
    )
    return candidates[0] if candidates else None


def refresh_material_result_reliability(
    db: Session, result: MaterialBatchTestResult
) -> tuple[str, list[str]]:
    issues: list[str] = []
    failures: list[str] = []
    batch = db.get(MaterialBatch, result.material_batch_id)
    definition = db.get(MaterialCharacteristicDefinition, result.characteristic_definition_id)
    method = db.get(MaterialTestMethod, result.method_id)
    specification = (
        matching_active_specification(
            db,
            batch,
            result.characteristic_definition_id,
            result.method_id,
            result.tested_at,
        )
        if batch
        else None
    )
    if not batch:
        failures.append("材料批次不存在")
    if not definition or definition.status != "ACTIVE":
        failures.append("材料特性定义不存在或未生效")
    if not method or method.status != "ACTIVE":
        failures.append("材料检测方法不存在或未生效")
    if definition and method and method.characteristic_definition_id != definition.id:
        failures.append("检测方法与材料特性定义不匹配")
    if definition and result.unit != definition.canonical_unit:
        failures.append("结果单位与材料特性规范单位不一致")
    if method and result.unit != method.result_unit:
        failures.append("结果单位与检测方法结果单位不一致")
    if method and not method.procedure_uri:
        issues.append("材料检测方法缺少批准规程来源")
    if not specification:
        issues.append("缺少检测时间有效的批准材料规格")
    elif (
        not specification.source_uri
        or not specification.effective_from
        or not specification.approved_by
        or not specification.approved_at
    ):
        issues.append("材料规格缺少来源、生效时间或审批证据")
    if not result.source_uri:
        issues.append("缺少批次检测结果来源文件")

    result.specification_id = specification.id if specification else None
    result.is_within_spec = None
    if specification:
        within = True
        if specification.lower_limit is not None and result.result_value < specification.lower_limit:
            within = False
        if specification.upper_limit is not None and result.result_value > specification.upper_limit:
            within = False
        if specification.lower_limit is not None or specification.upper_limit is not None:
            result.is_within_spec = within
        if not within:
            failures.append("批次检测结果超出批准材料规格")

    all_issues = failures + issues
    # Day-1: soft provenance gaps (source URI / approved spec metadata) stay informational.
    # Only hard failures keep the result out of feature aggregation.
    status = "FAILED" if failures else "VERIFIED"
    result.reliability_status = status
    result.reliability_issues = all_issues
    db.flush()
    return status, all_issues
