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
        stage_prefix = stage_run.process_stage.lower()
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
            actual_by_code = {parameter.parameter_code: parameter for parameter in actual_parameters}
            parameter_codes = {parameter.parameter_code for parameter in configured_parameters} | set(
                actual_by_code
            )
            configured_by_code = {
                parameter.parameter_code: parameter for parameter in configured_parameters
            }

            for parameter_code in parameter_codes:
                if is_out_of_scope_name(parameter_code):
                    continue
                actual = actual_by_code.get(parameter_code)
                configured = configured_by_code.get(parameter_code)
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
            if is_out_of_scope_name(parameter.parameter_code):
                continue
            feature_values[f"{stage_prefix}.{parameter.parameter_code}"] = parameter.actual_value
            stage_has_features = True

        for key, value in approved_numeric_values(stage_run.actual_parameters).items():
            feature_values[f"{stage_prefix}.{key}"] = value
            stage_has_features = True

        material = (
            db.get(MaterialBatch, stage_run.material_batch_id)
            if stage_run.material_batch_id
            else None
        )
        if material:
            if material.viscosity is not None:
                feature_values[f"{stage_prefix}.material_viscosity"] = material.viscosity
                stage_has_features = True
            if material.solid_ratio is not None:
                feature_values[f"{stage_prefix}.material_solid_ratio"] = material.solid_ratio
                stage_has_features = True
            for key, value in approved_numeric_values(material.coa_values).items():
                feature_values[f"{stage_prefix}.coa.{key}"] = value
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
