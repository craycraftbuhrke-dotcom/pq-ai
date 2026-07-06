from collections import defaultdict
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.scope_policy import (
    CURRENT_FEATURE_SET_VERSION,
    APPROVED_METRIC_KEYS,
    approved_numeric_values,
    is_out_of_scope_name,
    require_approved_quality_type,
)
from app.models.domain import (
    ActualParameter,
    Brush,
    BrushParameter,
    BrushPointContribution,
    MaterialBatch,
    MaterialBatchTestResult,
    MaterialCharacteristicApplicability,
    MaterialCharacteristicDefinition,
    MaterialSpecification,
    MeasurementPoint,
    PathSegmentExecution,
    PointContributionEntry,
    PointContributionVersion,
    PointFeatureSnapshot,
    ProcessStage,
    ProductionDeviceExecution,
    ProductionRun,
    ProductionStageRun,
    QualityMeasurement,
    QualityMetricValue,
    TrajectoryPathSegment,
    TrajectoryProgram,
)

STAGE_FEATURE_PREFIXES = {
    "MIDCOAT_EXT": "midcoat",
    "BASECOAT_1": "basecoat_1",
    "BASECOAT_2": "basecoat_2",
    "CLEARCOAT_1": "clearcoat_1",
    "CLEARCOAT_2": "clearcoat_2",
}


def _stage_feature_prefix(process_stage: str) -> str:
    return STAGE_FEATURE_PREFIXES.get(process_stage, process_stage.lower())


def _canonical_parameter_code(stage_prefix: str, parameter_code: str) -> str:
    code = parameter_code.strip()
    candidate_prefixes = [stage_prefix]
    if stage_prefix == "midcoat":
        candidate_prefixes.append("midcoat_ext")
    for prefix in candidate_prefixes:
        scoped_prefix = f"{prefix}_"
        if code.startswith(scoped_prefix):
            return code[len(scoped_prefix) :]
    return code


def build_point_feature_snapshot(
    db: Session,
    production_run_id: str,
    measurement_point_id: str,
    target_family: str = "ORANGE_PEEL",
    feature_set_version: str = CURRENT_FEATURE_SET_VERSION,
) -> dict:
    if feature_set_version != CURRENT_FEATURE_SET_VERSION:
        raise HTTPException(
            status_code=422,
            detail=(
                f"特征版本 {feature_set_version} 未获当前范围策略批准；"
                f"请使用 {CURRENT_FEATURE_SET_VERSION}"
            ),
        )
    production_run = db.get(ProductionRun, production_run_id)
    if not production_run:
        raise HTTPException(status_code=404, detail="生产事件不存在")
    if not db.get(MeasurementPoint, measurement_point_id):
        raise HTTPException(status_code=404, detail="测量点不存在")
    try:
        require_approved_quality_type(target_family)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    feature_values: dict[str, float] = {}
    stage_coverage: set[str] = set()
    contribution_count = 0
    lineage: dict[str, list | bool] = {
        "program_version_ids": [],
        "contribution_version_ids": [],
        "trajectory_program_ids": [],
        "device_execution_ids": [],
        "material_batch_ids": [],
        "material_result_ids": [],
        "material_specification_ids": [],
        "legacy_contribution_fallback": False,
    }

    stage_runs = list(
        db.scalars(
            select(ProductionStageRun).where(
                ProductionStageRun.production_run_id == production_run_id
            )
        )
    )
    for stage_run in stage_runs:
        stage_prefix = _stage_feature_prefix(stage_run.process_stage)
        stage_has_features = False
        weighted_sums: dict[str, float] = defaultdict(float)
        weight_sums: dict[str, float] = defaultdict(float)
        if stage_run.program_version_id not in lineage["program_version_ids"]:
            lineage["program_version_ids"].append(stage_run.program_version_id)
        device_execution = db.scalar(
            select(ProductionDeviceExecution).where(
                ProductionDeviceExecution.production_stage_run_id == stage_run.id
            )
        )
        if device_execution:
            if device_execution.status == "CHECKSUM_MISMATCH":
                raise HTTPException(
                    status_code=422,
                    detail=f"工序 {stage_run.process_stage} 实际轨迹校验和与批准轨迹不一致",
                )
            lineage["device_execution_ids"].append(device_execution.id)
            lineage["trajectory_program_ids"].append(device_execution.trajectory_program_id)

        contribution_version = db.scalar(
            select(PointContributionVersion)
            .where(
                PointContributionVersion.program_version_id == stage_run.program_version_id,
                PointContributionVersion.target_family == target_family,
                PointContributionVersion.status == "ACTIVE",
            )
            .order_by(PointContributionVersion.approved_at.desc())
        )
        source_rows: list[tuple[float, Brush | None, TrajectoryPathSegment | None]] = []
        if contribution_version:
            lineage["contribution_version_ids"].append(contribution_version.id)
            contribution_entries = list(
                db.scalars(
                    select(PointContributionEntry).where(
                        PointContributionEntry.contribution_version_id
                        == contribution_version.id,
                        PointContributionEntry.measurement_point_id == measurement_point_id,
                    )
                )
            )
            for entry in contribution_entries:
                path_segment = (
                    db.get(TrajectoryPathSegment, entry.path_segment_id)
                    if entry.path_segment_id
                    else None
                )
                brush = (
                    db.get(Brush, entry.brush_id)
                    if entry.brush_id
                    else db.get(Brush, path_segment.brush_id)
                    if path_segment and path_segment.brush_id
                    else None
                )
                source_rows.append((entry.contribution_weight, brush, path_segment))
        else:
            lineage["legacy_contribution_fallback"] = True
            legacy_rows = db.execute(
                select(BrushPointContribution, Brush)
                .join(Brush, Brush.id == BrushPointContribution.brush_id)
                .where(
                    Brush.program_version_id == stage_run.program_version_id,
                    BrushPointContribution.measurement_point_id == measurement_point_id,
                    BrushPointContribution.is_approved.is_(True),
                )
            ).all()
            source_rows = [
                (contribution.contribution_weight, brush, None)
                for contribution, brush in legacy_rows
            ]
        contribution_count += len(source_rows)

        for contribution_weight, brush, path_segment in source_rows:
            if path_segment and path_segment.configured_speed is not None:
                speed = path_segment.configured_speed
                if device_execution:
                    segment_execution = db.scalar(
                        select(PathSegmentExecution).where(
                            PathSegmentExecution.device_execution_id == device_execution.id,
                            PathSegmentExecution.path_segment_id == path_segment.id,
                        )
                    )
                    if segment_execution and segment_execution.actual_speed is not None:
                        speed = segment_execution.actual_speed
                weighted_sums["trajectory_path_speed"] += speed * contribution_weight
                weight_sums["trajectory_path_speed"] += contribution_weight
                trajectory = db.get(TrajectoryProgram, path_segment.trajectory_program_id)
                if trajectory and trajectory.id not in lineage["trajectory_program_ids"]:
                    lineage["trajectory_program_ids"].append(trajectory.id)
            if not brush:
                continue
            configured_parameters = list(
                db.scalars(select(BrushParameter).where(BrushParameter.brush_id == brush.id))
            )
            actual_parameters = list(
                db.scalars(
                    select(ActualParameter).where(
                        ActualParameter.production_stage_run_id == stage_run.id,
                        ActualParameter.brush_id == brush.id,
                    )
                )
            )
            configured_by_code = {
                _canonical_parameter_code(stage_prefix, parameter.parameter_code): parameter
                for parameter in configured_parameters
            }
            actual_by_code = {
                _canonical_parameter_code(stage_prefix, parameter.parameter_code): parameter
                for parameter in actual_parameters
            }
            parameter_codes = set(configured_by_code) | set(actual_by_code)

            for parameter_code in parameter_codes:
                if is_out_of_scope_name(parameter_code):
                    continue
                actual = actual_by_code.get(parameter_code)
                configured = configured_by_code.get(parameter_code)
                source_code = (
                    actual.parameter_code
                    if actual
                    else configured.parameter_code
                    if configured
                    else parameter_code
                )
                if is_out_of_scope_name(source_code):
                    continue
                value = actual.actual_value if actual else configured.configured_value
                weighted_sums[parameter_code] += value * contribution_weight
                weight_sums[parameter_code] += contribution_weight

        for parameter_code, weighted_sum in weighted_sums.items():
            feature_values[f"{stage_prefix}.{parameter_code}"] = (
                weighted_sum / weight_sums[parameter_code]
            )
            stage_has_features = True

        stage_actuals = list(
            db.scalars(
                select(ActualParameter).where(
                    ActualParameter.production_stage_run_id == stage_run.id,
                    ActualParameter.brush_id.is_(None),
                )
            )
        )
        for parameter in stage_actuals:
            parameter_code = _canonical_parameter_code(stage_prefix, parameter.parameter_code)
            if is_out_of_scope_name(parameter.parameter_code) or is_out_of_scope_name(parameter_code):
                continue
            feature_values[f"{stage_prefix}.{parameter_code}"] = parameter.actual_value
            stage_has_features = True

        for key, value in approved_numeric_values(stage_run.actual_parameters).items():
            parameter_code = _canonical_parameter_code(stage_prefix, key)
            feature_values[f"{stage_prefix}.{parameter_code}"] = value
            stage_has_features = True

        material = (
            db.get(MaterialBatch, stage_run.material_batch_id)
            if stage_run.material_batch_id
            else None
        )
        if material:
            if material.id not in lineage["material_batch_ids"]:
                lineage["material_batch_ids"].append(material.id)
            applicabilities = list(
                db.scalars(
                    select(MaterialCharacteristicApplicability).where(
                        MaterialCharacteristicApplicability.material_type
                        == material.material_type,
                        MaterialCharacteristicApplicability.process_stage
                        == stage_run.process_stage,
                        MaterialCharacteristicApplicability.target_family == target_family,
                        MaterialCharacteristicApplicability.status == "ACTIVE",
                        MaterialCharacteristicApplicability.approved_by.is_not(None),
                        MaterialCharacteristicApplicability.approved_at.is_not(None),
                    )
                )
            )
            for applicability in applicabilities:
                definition = db.get(
                    MaterialCharacteristicDefinition,
                    applicability.characteristic_definition_id,
                )
                result = db.scalar(
                    select(MaterialBatchTestResult)
                    .where(
                        MaterialBatchTestResult.material_batch_id == material.id,
                        MaterialBatchTestResult.characteristic_definition_id
                        == applicability.characteristic_definition_id,
                        MaterialBatchTestResult.reliability_status == "VERIFIED",
                        MaterialBatchTestResult.tested_at <= production_run.started_at,
                    )
                    .order_by(MaterialBatchTestResult.tested_at.desc())
                )
                specification = (
                    db.get(MaterialSpecification, result.specification_id)
                    if result and result.specification_id
                    else None
                )
                if (
                    not definition
                    or definition.status != "ACTIVE"
                    or not definition.is_model_feature
                    or not result
                    or not specification
                    or specification.status != "ACTIVE"
                ):
                    if applicability.is_required:
                        raise HTTPException(
                            status_code=422,
                            detail=(
                                f"工序 {stage_run.process_stage} 缺少生产前已验证的必需材料特性"
                                f" {definition.code if definition else applicability.characteristic_definition_id}"
                            ),
                        )
                    continue
                feature_values[f"{stage_prefix}.material.{definition.code}"] = (
                    result.result_value
                )
                if result.id not in lineage["material_result_ids"]:
                    lineage["material_result_ids"].append(result.id)
                if specification.id not in lineage["material_specification_ids"]:
                    lineage["material_specification_ids"].append(specification.id)
                stage_has_features = True

        if stage_has_features:
            stage_coverage.add(stage_run.process_stage)

    quality_labels: dict[str, float] = {}
    quality_rows = db.execute(
        select(QualityMetricValue, QualityMeasurement)
        .join(QualityMeasurement, QualityMeasurement.id == QualityMetricValue.measurement_id)
        .where(
            QualityMeasurement.production_run_id == production_run_id,
            QualityMeasurement.measurement_point_id == measurement_point_id,
            QualityMeasurement.quality_type == target_family,
            QualityMeasurement.is_valid.is_(True),
            QualityMeasurement.reliability_status == "VERIFIED",
        )
        .order_by(QualityMeasurement.measured_at)
    ).all()
    for metric, measurement in quality_rows:
        if (measurement.quality_type, metric.metric_code) not in APPROVED_METRIC_KEYS:
            continue
        quality_labels[metric.metric_code] = (
            metric.corrected_value if metric.corrected_value is not None else metric.raw_value
        )

    generated_at = datetime.now(UTC)
    completeness_score = round(len(stage_coverage) / len(ProcessStage), 4)
    snapshot = db.scalar(
        select(PointFeatureSnapshot).where(
            PointFeatureSnapshot.production_run_id == production_run_id,
            PointFeatureSnapshot.measurement_point_id == measurement_point_id,
            PointFeatureSnapshot.feature_set_version == feature_set_version,
            PointFeatureSnapshot.target_family == target_family,
        )
    )
    if snapshot:
        snapshot.feature_values = feature_values
        snapshot.lineage = lineage
        snapshot.completeness_score = completeness_score
        snapshot.generated_at = generated_at
    else:
        snapshot = PointFeatureSnapshot(
            production_run_id=production_run_id,
            measurement_point_id=measurement_point_id,
            feature_set_version=feature_set_version,
            target_family=target_family,
            feature_values=feature_values,
            lineage=lineage,
            completeness_score=completeness_score,
            generated_at=generated_at,
        )
        db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {
        "snapshot_id": snapshot.id,
        "production_run_id": production_run_id,
        "measurement_point_id": measurement_point_id,
        "feature_set_version": feature_set_version,
        "target_family": target_family,
        "feature_values": feature_values,
        "lineage": lineage,
        "quality_labels": quality_labels,
        "completeness_score": completeness_score,
        "generated_at": generated_at,
        "stage_coverage": sorted(stage_coverage),
        "contribution_count": contribution_count,
    }
