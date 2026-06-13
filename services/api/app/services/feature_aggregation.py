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
)
from app.models.domain import (
    ActualParameter,
    Brush,
    BrushParameter,
    BrushPointContribution,
    MaterialBatch,
    MeasurementPoint,
    PointFeatureSnapshot,
    ProcessStage,
    ProductionRun,
    ProductionStageRun,
    QualityMeasurement,
    QualityMetricValue,
)


def build_point_feature_snapshot(
    db: Session,
    production_run_id: str,
    measurement_point_id: str,
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

    feature_values: dict[str, float] = {}
    stage_coverage: set[str] = set()
    contribution_count = 0

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

        contribution_rows = db.execute(
            select(BrushPointContribution, Brush)
            .join(Brush, Brush.id == BrushPointContribution.brush_id)
            .where(
                Brush.program_version_id == stage_run.program_version_id,
                BrushPointContribution.measurement_point_id == measurement_point_id,
                BrushPointContribution.is_approved.is_(True),
            )
        ).all()
        contribution_count += len(contribution_rows)

        for contribution, brush in contribution_rows:
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
                weighted_sums[parameter_code] += value * contribution.contribution_weight
                weight_sums[parameter_code] += contribution.contribution_weight

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
            QualityMeasurement.is_valid.is_(True),
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
        )
    )
    if snapshot:
        snapshot.feature_values = feature_values
        snapshot.completeness_score = completeness_score
        snapshot.generated_at = generated_at
    else:
        snapshot = PointFeatureSnapshot(
            production_run_id=production_run_id,
            measurement_point_id=measurement_point_id,
            feature_set_version=feature_set_version,
            feature_values=feature_values,
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
        "feature_values": feature_values,
        "quality_labels": quality_labels,
        "completeness_score": completeness_score,
        "generated_at": generated_at,
        "stage_coverage": sorted(stage_coverage),
        "contribution_count": contribution_count,
    }
