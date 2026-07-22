import hashlib
import json
from datetime import UTC, datetime
from math import ceil, sqrt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.scope_policy import (
    ScopeViolation,
    approved_numeric_values,
    require_scope_safe_model,
    target_family_for_metric,
)
from app.models.domain import (
    DatasetSnapshot,
    DatasetSplitMember,
    DiagnosisResult,
    Color,
    Factory,
    FactoryVehicleModel,
    MeasurementPoint,
    ModelArtifact,
    ModelAcceptancePolicy,
    ModelApplicabilityScope,
    ModelAcceptanceDecision,
    ModelOodPolicy,
    ModelValidationFold,
    ModelVersion,
    ParameterConstraintSource,
    ParameterDefinition,
    PointFeatureSnapshot,
    PredictionResult,
    QualityMeasurement,
    QualityMetricValue,
    QualityMetricDefinition,
    ProductionRun,
    Recommendation,
    RecommendationAction,
    TrainingDataUpload,
    TrainingWideSample,
    VehicleModel,
    VehicleModelColor,
)
from app.services.measurement_reliability import refresh_measurement_reliability
from app.services.quality_evaluation import resolve_quality_standard


def _time_key(value: datetime) -> float:
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value).timestamp()


def _ensure_model_scope(model: ModelVersion) -> None:
    try:
        require_scope_safe_model(
            model.target_metric,
            model.feature_set_version,
            model.model_payload.get("feature_names", []),
        )
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _target_family(target_metric: str) -> str:
    try:
        return target_family_for_metric(target_metric)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _utc_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _resolve_constraint_source(
    db: Session,
    definition: ParameterDefinition,
    factory_id: str,
    process_stage: str,
    as_of: datetime,
) -> ParameterConstraintSource | None:
    as_of_utc = _utc_datetime(as_of)
    sources = list(
        db.scalars(
            select(ParameterConstraintSource).where(
                ParameterConstraintSource.parameter_definition_id == definition.id,
                ParameterConstraintSource.status == "ACTIVE",
            )
        )
    )
    eligible = []
    for source in sources:
        if source.factory_id not in (None, factory_id):
            continue
        if source.process_stage not in (None, process_stage):
            continue
        if source.effective_from and _utc_datetime(source.effective_from) > as_of_utc:
            continue
        if source.effective_to and _utc_datetime(source.effective_to) <= as_of_utc:
            continue
        eligible.append(source)
    eligible.sort(
        key=lambda source: (
            source.factory_id == factory_id,
            source.process_stage == process_stage,
            _utc_datetime(source.effective_from).timestamp() if source.effective_from else 0,
        ),
        reverse=True,
    )
    return eligible[0] if eligible else None


def _target_value(
    db: Session, production_run_id: str, measurement_point_id: str, target_metric: str
) -> float | None:
    observation = _target_observation(
        db, production_run_id, measurement_point_id, target_metric
    )
    return observation["value"] if observation else None


def _target_observation(
    db: Session, production_run_id: str, measurement_point_id: str, target_metric: str
) -> dict | None:
    for measurement in db.scalars(
        select(QualityMeasurement).where(
            QualityMeasurement.production_run_id == production_run_id,
            QualityMeasurement.measurement_point_id == measurement_point_id,
            QualityMeasurement.is_valid.is_(True),
        )
    ):
        refresh_measurement_reliability(db, measurement)

    row = db.execute(
        select(QualityMetricValue, QualityMeasurement)
        .join(QualityMeasurement, QualityMeasurement.id == QualityMetricValue.measurement_id)
        .where(
            QualityMeasurement.production_run_id == production_run_id,
            QualityMeasurement.measurement_point_id == measurement_point_id,
            QualityMeasurement.is_valid.is_(True),
            QualityMeasurement.reliability_status == "VERIFIED",
            QualityMetricValue.metric_code == target_metric,
        )
        .order_by(QualityMeasurement.measured_at.desc())
    ).first()
    if not row:
        return None
    metric, measurement = row
    return {
        "value": metric.corrected_value if metric.corrected_value is not None else metric.raw_value,
        "measurement_id": measurement.id,
        "measured_at": measurement.measured_at,
    }


def _regression_metrics(predictions: list[float], targets: list[float], prefix: str) -> dict:
    metrics = _regression_metric_values(predictions, targets)
    return {f"{prefix}_{key}": value for key, value in metrics.items()}


def _regression_metric_values(predictions: list[float], targets: list[float]) -> dict:
    errors = [prediction - target for prediction, target in zip(predictions, targets, strict=True)]
    mean_target = sum(targets) / len(targets)
    total_variance = sum((target - mean_target) ** 2 for target in targets)
    residual_variance = sum(error**2 for error in errors)
    return {
        "mae": round(sum(abs(error) for error in errors) / len(errors), 6),
        "rmse": round(sqrt(residual_variance / len(errors)), 6),
        "r2": round(
            1 - residual_variance / total_variance
            if total_variance
            else (1.0 if residual_variance == 0 else 0.0),
            6,
        ),
    }


def _model_artifact_source(model: ModelVersion) -> dict:
    return {
        "model_code": model.model_code,
        "version": model.version,
        "model_type": model.model_type,
        "target_metric": model.target_metric,
        "feature_set_version": model.feature_set_version,
        "dataset_snapshot_id": model.dataset_snapshot_id,
        "training_sample_count": model.training_sample_count,
        "model_payload": model.model_payload,
        "evaluation_metrics": model.evaluation_metrics,
    }


def _model_payload_hash(model: ModelVersion) -> str:
    serialized = json.dumps(
        _model_artifact_source(model),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _register_model_artifact(db: Session, model: ModelVersion) -> ModelArtifact:
    payload_hash = _model_payload_hash(model)
    artifact = ModelArtifact(
        model_version_id=model.id,
        artifact_type="LINEAR_MODEL_PAYLOAD",
        artifact_uri=f"mysql://model-artifact/{model.id}/linear-model-payload.json",
        storage_backend="MYSQL",
        payload_hash=payload_hash,
        metadata_payload={
            "hash_algorithm": "SHA256",
            "model_code": model.model_code,
            "version": model.version,
            "model_type": model.model_type,
            "dataset_snapshot_id": model.dataset_snapshot_id,
            "feature_count": len(model.model_payload.get("feature_names", [])),
            "evidence_included": [
                "model_payload",
                "evaluation_metrics",
                "dataset_snapshot_id",
                "training_sample_count",
            ],
        },
        status="REGISTERED",
        created_by="model-training-service",
        registered_at=datetime.now(UTC),
        remark="不可变模型载荷登记。哈希覆盖模型参数、评估指标和训练数据集引用。",
    )
    db.add(artifact)
    model.artifact_uri = artifact.artifact_uri
    db.flush()
    return artifact


def _model_artifact_evidence(db: Session, model: ModelVersion) -> dict:
    artifact = db.scalar(
        select(ModelArtifact)
        .where(
            ModelArtifact.model_version_id == model.id,
            ModelArtifact.status == "REGISTERED",
        )
        .order_by(ModelArtifact.registered_at.desc())
    )
    expected_hash = _model_payload_hash(model)
    return {
        "registered": artifact is not None,
        "artifact_id": artifact.id if artifact else None,
        "artifact_uri": artifact.artifact_uri if artifact else None,
        "payload_hash": artifact.payload_hash if artifact else None,
        "expected_hash": expected_hash,
        "hash_matches": artifact is not None and artifact.payload_hash == expected_hash,
        "status": artifact.status if artifact else "MISSING",
    }


def _multi_axis_validation_evidence(model: ModelVersion) -> dict:
    summary = model.evaluation_metrics.get("multi_axis_validation") or {}
    axes = summary.get("axes", {})
    evaluated_axes = [
        {"axis": axis, **axis_summary}
        for axis, axis_summary in axes.items()
        if axis_summary.get("status") == "EVALUATED"
    ]
    rmse_values = [
        float(axis["rmse"])
        for axis in evaluated_axes
        if axis.get("rmse") is not None
    ]
    r2_values = [
        float(axis["r2"])
        for axis in evaluated_axes
        if axis.get("r2") is not None
    ]
    return {
        "report_present": bool(axes),
        "axis_count": len(axes),
        "evaluated_axis_count": len(evaluated_axes),
        "insufficient_axes": [
            axis
            for axis, axis_summary in axes.items()
            if axis_summary.get("status") == "INSUFFICIENT_AXIS_DIVERSITY"
        ],
        "worst_rmse": max(rmse_values) if rmse_values else None,
        "worst_r2": min(r2_values) if r2_values else None,
        "axes": axes,
    }


def _create_validation_folds(
    db: Session,
    model: ModelVersion,
    dataset: DatasetSnapshot,
    *,
    model_config: dict,
    min_train_samples: int,
    time_holdout_metrics: dict,
) -> dict:
    members = list(
        db.scalars(
            select(DatasetSplitMember).where(
                DatasetSplitMember.dataset_snapshot_id == dataset.id
            )
        )
    )
    production_run_ids = {
        member.production_run_id for member in members if member.production_run_id
    }
    runs_by_id = (
        {
            run.id: run
            for run in db.scalars(
                select(ProductionRun).where(ProductionRun.id.in_(production_run_ids))
            )
        }
        if production_run_ids
        else {}
    )
    manual_sample_ids = {
        member.manual_sample_id for member in members if member.manual_sample_id
    }
    samples_by_id = (
        {
            sample.id: sample
            for sample in db.scalars(
                select(TrainingWideSample).where(
                    TrainingWideSample.id.in_(manual_sample_ids)
                )
            )
        }
        if manual_sample_ids
        else {}
    )

    def context_ids(
        member: DatasetSplitMember, run: ProductionRun | None
    ) -> tuple[str | None, str | None, str | None]:
        if run is not None:
            return run.factory_id, run.vehicle_model_id, run.color_id
        sample = samples_by_id.get(member.manual_sample_id) if member.manual_sample_id else None
        if sample is None:
            return None, None, None
        return sample.factory_id, sample.vehicle_model_id, sample.color_id

    rows = [(member, runs_by_id.get(member.production_run_id)) for member in members]
    now = datetime.now(UTC)
    summaries: dict[str, dict] = {}

    def add_fold(
        axis: str,
        fold_key: str,
        train_items: list[tuple[DatasetSplitMember, ProductionRun | None]],
        validation_items: list[tuple[DatasetSplitMember, ProductionRun | None]],
        status: str,
        metrics: dict,
    ) -> None:
        db.add(
            ModelValidationFold(
                model_version_id=model.id,
                dataset_snapshot_id=dataset.id,
                validation_axis=axis,
                fold_key=fold_key[:120],
                train_sample_count=len(train_items),
                validation_sample_count=len(validation_items),
                train_group_count=len({member.group_value for member, _run in train_items}),
                validation_group_count=len(
                    {member.group_value for member, _run in validation_items}
                ),
                metrics=metrics,
                status=status,
                evaluated_at=now,
            )
        )

    def samples(
        items: list[tuple[DatasetSplitMember, ProductionRun | None]]
    ) -> list[tuple[dict[str, float], float]]:
        return [(member.feature_values, member.target_value) for member, _run in items]

    train_items = [(member, run) for member, run in rows if member.split == "TRAIN"]
    validation_items = [
        (member, run) for member, run in rows if member.split == "VALIDATION"
    ]
    time_metrics = {
        "mae": time_holdout_metrics["validation_mae"],
        "rmse": time_holdout_metrics["validation_rmse"],
        "r2": time_holdout_metrics["validation_r2"],
        "source": "PRIMARY_TEMPORAL_HOLDOUT",
    }
    add_fold(
        "TIME_HOLDOUT",
        "TEMPORAL_GROUPED_HOLDOUT",
        train_items,
        validation_items,
        "EVALUATED",
        time_metrics,
    )
    summaries["TIME_HOLDOUT"] = {
        "status": "EVALUATED",
        "fold_count": 1,
        "evaluated_fold_count": 1,
        "validation_sample_count": len(validation_items),
        "rmse": time_metrics["rmse"],
        "mae": time_metrics["mae"],
        "r2": time_metrics["r2"],
    }

    axis_definitions = {
        "FACTORY": lambda member, run: context_ids(member, run)[0],
        "VEHICLE_MODEL": lambda member, run: context_ids(member, run)[1],
        "COLOR": lambda member, run: context_ids(member, run)[2],
        "PRODUCTION_GROUP_LOO": lambda member, run: member.group_value,
    }
    for axis, key_getter in axis_definitions.items():
        all_keyed_rows = [(key_getter(member, run), member, run) for member, run in rows]
        keyed_rows = [item for item in all_keyed_rows if item[0] is not None]
        excluded_sample_count = len(all_keyed_rows) - len(keyed_rows)
        distinct_keys = sorted({key for key, _member, _run in keyed_rows})
        if len(distinct_keys) < 2:
            add_fold(
                axis,
                "ALL",
                [],
                [(member, run) for _key, member, run in keyed_rows],
                "INSUFFICIENT_AXIS_DIVERSITY",
                {
                    "distinct_key_count": len(distinct_keys),
                    "excluded_sample_count": excluded_sample_count,
                    "reason": "该验证轴只有一个取值，不能估计跨域泛化能力。",
                },
            )
            summaries[axis] = {
                "status": "INSUFFICIENT_AXIS_DIVERSITY",
                "fold_count": 1,
                "evaluated_fold_count": 0,
                "distinct_key_count": len(distinct_keys),
                "excluded_sample_count": excluded_sample_count,
                "validation_sample_count": 0,
                "rmse": None,
                "mae": None,
                "r2": None,
            }
            continue

        aggregate_predictions: list[float] = []
        aggregate_targets: list[float] = []
        evaluated_fold_count = 0
        skipped_fold_count = 0
        for fold_key in distinct_keys:
            fold_train_items = [
                (member, run) for key, member, run in keyed_rows if key != fold_key
            ]
            fold_validation_items = [
                (member, run) for key, member, run in keyed_rows if key == fold_key
            ]
            if len(fold_train_items) < min_train_samples:
                skipped_fold_count += 1
                add_fold(
                    axis,
                    fold_key,
                    fold_train_items,
                    fold_validation_items,
                    "INSUFFICIENT_TRAINING_SUPPORT",
                    {
                        "min_train_samples": min_train_samples,
                        "reason": "留出该折后训练样本不足，未计算指标。",
                    },
                )
                continue
            try:
                fold_model = _fit_selected_linear(samples(fold_train_items), model_config)
                predictions = _predict_samples(fold_model, samples(fold_validation_items))
            except HTTPException as exc:
                skipped_fold_count += 1
                add_fold(
                    axis,
                    fold_key,
                    fold_train_items,
                    fold_validation_items,
                    "FAILED",
                    {"reason": str(exc.detail)},
                )
                continue
            targets = [member.target_value for member, _run in fold_validation_items]
            metrics = _regression_metric_values(predictions, targets)
            aggregate_predictions.extend(predictions)
            aggregate_targets.extend(targets)
            evaluated_fold_count += 1
            add_fold(
                axis,
                fold_key,
                fold_train_items,
                fold_validation_items,
                "EVALUATED",
                metrics,
            )

        if aggregate_predictions:
            aggregate_metrics = _regression_metric_values(
                aggregate_predictions, aggregate_targets
            )
            summaries[axis] = {
                "status": "EVALUATED",
                "fold_count": len(distinct_keys),
                "evaluated_fold_count": evaluated_fold_count,
                "skipped_fold_count": skipped_fold_count,
                "distinct_key_count": len(distinct_keys),
                "excluded_sample_count": excluded_sample_count,
                "validation_sample_count": len(aggregate_targets),
                **aggregate_metrics,
            }
        else:
            summaries[axis] = {
                "status": "NO_EVALUATED_FOLDS",
                "fold_count": len(distinct_keys),
                "evaluated_fold_count": 0,
                "skipped_fold_count": skipped_fold_count,
                "distinct_key_count": len(distinct_keys),
                "excluded_sample_count": excluded_sample_count,
                "validation_sample_count": 0,
                "rmse": None,
                "mae": None,
                "r2": None,
            }

    evaluated_summaries = [
        axis_summary
        for axis_summary in summaries.values()
        if axis_summary.get("status") == "EVALUATED"
    ]
    return {
        "strategy": "TEMPORAL_HOLDOUT_PLUS_LEAVE_AXIS_OUT",
        "axes": summaries,
        "evaluated_axis_count": len(evaluated_summaries),
        "insufficient_axis_count": sum(
            axis_summary.get("status") == "INSUFFICIENT_AXIS_DIVERSITY"
            for axis_summary in summaries.values()
        ),
        "worst_rmse": max(
            (axis_summary["rmse"] for axis_summary in evaluated_summaries),
            default=None,
        ),
        "worst_r2": min(
            (axis_summary["r2"] for axis_summary in evaluated_summaries),
            default=None,
        ),
    }


def _predict_samples(model_payload: dict, samples: list[tuple[dict[str, float], float]]) -> list[float]:
    predictions = []
    for feature_values, _target in samples:
        normalized = [
            (float(feature_values.get(name, mean)) - mean) / scale
            for name, mean, scale in zip(
                model_payload["feature_names"],
                model_payload["means"],
                model_payload["scales"],
                strict=True,
            )
        ]
        predictions.append(
            model_payload["intercept"]
            + sum(
                coefficient * value
                for coefficient, value in zip(
                    model_payload["coefficients"], normalized, strict=True
                )
            )
        )
    return predictions


def _soft_threshold(value: float, threshold: float) -> float:
    if value > threshold:
        return value - threshold
    if value < -threshold:
        return value + threshold
    return 0.0


def _fit_regularized_linear(
    samples: list[tuple[dict[str, float], float]],
    regularization_strength: float,
    l1_ratio: float,
    model_family: str,
) -> dict:
    common_features = set(samples[0][0])
    for feature_values, _target in samples[1:]:
        common_features &= set(feature_values)
    feature_names = sorted(common_features)
    if not feature_names:
        raise HTTPException(status_code=422, detail="训练样本没有共同数值特征")

    columns = [[sample[0][name] for sample in samples] for name in feature_names]
    means = [sum(column) / len(column) for column in columns]
    scales = [
        sqrt(sum((value - mean) ** 2 for value in column) / len(column)) or 1.0
        for column, mean in zip(columns, means, strict=True)
    ]
    x_rows = [
        [
            (feature_values[name] - mean) / scale
            for name, mean, scale in zip(feature_names, means, scales, strict=True)
        ]
        for feature_values, _target in samples
    ]
    targets = [target for _features, target in samples]
    intercept = sum(targets) / len(targets)
    centered_targets = [target - intercept for target in targets]
    coefficients = [0.0] * len(feature_names)

    l1_penalty = regularization_strength * l1_ratio
    l2_penalty = regularization_strength * (1 - l1_ratio)
    residuals = centered_targets.copy()
    # Residual-updating coordinate descent keeps small industrial wide tables fast
    # while avoiding a heavy numerical runtime dependency in the API image.
    for _iteration in range(500):
        max_change = 0.0
        for feature_index in range(len(feature_names)):
            previous = coefficients[feature_index]
            if previous:
                for row_index, row in enumerate(x_rows):
                    residuals[row_index] += previous * row[feature_index]
            numerator = sum(
                row[feature_index] * residual
                for row, residual in zip(x_rows, residuals, strict=True)
            )
            denominator = (
                sum(row[feature_index] ** 2 for row in x_rows) + l2_penalty
            )
            current = (
                _soft_threshold(numerator, l1_penalty) / denominator
                if denominator
                else 0.0
            )
            coefficients[feature_index] = current
            for row_index, row in enumerate(x_rows):
                residuals[row_index] -= current * row[feature_index]
            max_change = max(max_change, abs(current - previous))
        if max_change < 1e-9:
            break

    fitted = {
        "feature_names": feature_names,
        "means": means,
        "scales": scales,
        "minimums": [min(column) for column in columns],
        "maximums": [max(column) for column in columns],
        "coefficients": coefficients,
        "intercept": intercept,
        "model_family": model_family,
        "regularization_strength": regularization_strength,
        "l1_ratio": l1_ratio,
    }
    predictions = _predict_samples(fitted, samples)
    metrics = _regression_metrics(predictions, targets, "training")
    fitted["residual_std"] = metrics["training_rmse"]
    fitted["evaluation_metrics"] = metrics
    return fitted


def _fit_ridge(samples: list[tuple[dict[str, float], float]], ridge_lambda: float) -> dict:
    return _fit_regularized_linear(samples, ridge_lambda, 0.0, "RIDGE")


def _fit_selected_linear(
    samples: list[tuple[dict[str, float], float]], config: dict
) -> dict:
    return _fit_regularized_linear(
        samples,
        float(config["regularization_strength"]),
        float(config["l1_ratio"]),
        str(config["model_family"]),
    )


def _temporal_tuning_folds(
    members: list[DatasetSplitMember],
) -> list[tuple[list[DatasetSplitMember], list[DatasetSplitMember]]]:
    grouped: dict[str, list[DatasetSplitMember]] = {}
    for member in members:
        grouped.setdefault(member.group_value, []).append(member)
    ordered_groups = sorted(
        grouped,
        key=lambda key: min(_time_key(item.occurred_at) for item in grouped[key]),
    )
    folds = []
    for validation_index in range(max(2, len(ordered_groups) - 3), len(ordered_groups)):
        train_groups = set(ordered_groups[:validation_index])
        validation_group = ordered_groups[validation_index]
        train_members = [item for item in members if item.group_value in train_groups]
        validation_members = grouped[validation_group]
        if len(train_members) >= 3 and validation_members:
            folds.append((train_members, validation_members))
    return folds


def _select_training_model(
    train_members: list[DatasetSplitMember],
    requested_family: str,
    regularization_strength: float,
    elastic_net_l1_ratio: float,
) -> tuple[dict, dict]:
    base_strength = max(float(regularization_strength), 0.0)
    if requested_family == "AUTO":
        strengths = (
            [0.0, 0.1, 1.0]
            if base_strength == 0
            else sorted({base_strength / 10, base_strength, base_strength * 10})
        )
        candidates = [
            {"model_family": "RIDGE", "regularization_strength": value, "l1_ratio": 0.0}
            for value in strengths
        ]
        candidates.extend(
            {
                "model_family": "ELASTIC_NET",
                "regularization_strength": value,
                "l1_ratio": ratio,
            }
            for value in strengths
            for ratio in (0.25, elastic_net_l1_ratio, 0.75)
        )
    else:
        candidates = [
            {
                "model_family": requested_family,
                "regularization_strength": base_strength,
                "l1_ratio": elastic_net_l1_ratio if requested_family == "ELASTIC_NET" else 0.0,
            }
        ]

    folds = _temporal_tuning_folds(train_members)
    candidate_reports = []
    for candidate in candidates:
        predictions: list[float] = []
        targets: list[float] = []
        for fold_train, fold_validation in folds:
            fitted = _fit_selected_linear(
                [(item.feature_values, item.target_value) for item in fold_train],
                candidate,
            )
            fold_samples = [
                (item.feature_values, item.target_value) for item in fold_validation
            ]
            predictions.extend(_predict_samples(fitted, fold_samples))
            targets.extend(item.target_value for item in fold_validation)
        metrics = (
            _regression_metric_values(predictions, targets)
            if predictions
            else {"mae": None, "rmse": None, "r2": None}
        )
        candidate_reports.append({**candidate, **metrics})

    selected = min(
        candidate_reports,
        key=lambda item: (
            item["rmse"] is None,
            item["rmse"] if item["rmse"] is not None else float("inf"),
            item["model_family"] != "RIDGE",
            item["regularization_strength"],
        ),
    )
    selected_config = {
        key: selected[key]
        for key in ("model_family", "regularization_strength", "l1_ratio")
    }
    fitted = _fit_selected_linear(
        [(item.feature_values, item.target_value) for item in train_members],
        selected_config,
    )
    return fitted, {
        "strategy": (
            "AUTO_TEMPORAL_INNER_VALIDATION"
            if requested_family == "AUTO"
            else "USER_SELECTED_FAMILY"
        ),
        "primary_holdout_used_for_selection": False,
        "inner_fold_count": len(folds),
        "inner_validation_sample_count": sum(len(validation) for _train, validation in folds),
        "candidate_count": len(candidate_reports),
        "selected": selected_config,
        "candidates": candidate_reports,
    }


def ensure_model_governance(
    db: Session,
    model: ModelVersion,
    *,
    max_abs_standardized_shift: float = 4.0,
    max_outlier_feature_ratio: float = 0.2,
    min_feature_completeness: float = 1.0,
) -> None:
    if not model.dataset_snapshot_id:
        raise HTTPException(status_code=409, detail="模型没有受治理的数据集，无法派生适用范围")
    existing_contexts = set(
        db.execute(
            select(
                ModelApplicabilityScope.factory_id,
                ModelApplicabilityScope.vehicle_model_id,
                ModelApplicabilityScope.color_id,
            ).where(ModelApplicabilityScope.model_version_id == model.id)
        ).all()
    )
    contexts = set(
        db.execute(
            select(
                ProductionRun.factory_id,
                ProductionRun.vehicle_model_id,
                ProductionRun.color_id,
            )
            .join(DatasetSplitMember, DatasetSplitMember.production_run_id == ProductionRun.id)
            .where(DatasetSplitMember.dataset_snapshot_id == model.dataset_snapshot_id)
        ).all()
    )
    contexts |= {
        (factory_id, vehicle_model_id, color_id)
        for factory_id, vehicle_model_id, color_id in db.execute(
            select(
                TrainingWideSample.factory_id,
                TrainingWideSample.vehicle_model_id,
                TrainingWideSample.color_id,
            )
            .join(
                DatasetSplitMember,
                DatasetSplitMember.manual_sample_id == TrainingWideSample.id,
            )
            .where(
                DatasetSplitMember.dataset_snapshot_id == model.dataset_snapshot_id,
                TrainingWideSample.factory_id.is_not(None),
                TrainingWideSample.vehicle_model_id.is_not(None),
                TrainingWideSample.color_id.is_not(None),
            )
        ).all()
    }
    for factory_id, vehicle_model_id, color_id in contexts - existing_contexts:
        db.add(
            ModelApplicabilityScope(
                model_version_id=model.id,
                factory_id=factory_id,
                vehicle_model_id=vehicle_model_id,
                color_id=color_id,
                status="PENDING",
                source="DATASET_DERIVED",
                remark="由受治理训练数据集中的生产或人工样本上下文自动派生，需随模型人工验收。",
            )
        )
    if not db.scalar(select(ModelOodPolicy).where(ModelOodPolicy.model_version_id == model.id)):
        db.add(
            ModelOodPolicy(
                model_version_id=model.id,
                max_abs_standardized_shift=max_abs_standardized_shift,
                max_outlier_feature_ratio=max_outlier_feature_ratio,
                min_feature_completeness=min_feature_completeness,
                action="BLOCK",
                status="PENDING",
                remark="统计分布外阻断策略，不代表设备、材料或工艺安全边界。",
            )
        )
    db.flush()


def create_model_applicability_scope(db: Session, model: ModelVersion, payload):
    if (
        not db.get(Factory, payload.factory_id)
        or not db.get(VehicleModel, payload.vehicle_model_id)
        or not db.get(Color, payload.color_id)
    ):
        raise HTTPException(status_code=422, detail="适用范围引用的工厂、车型或颜色不存在")
    if not db.scalar(
        select(FactoryVehicleModel).where(
            FactoryVehicleModel.factory_id == payload.factory_id,
            FactoryVehicleModel.vehicle_model_id == payload.vehicle_model_id,
            FactoryVehicleModel.is_active.is_(True),
        )
    ) or not db.scalar(
        select(VehicleModelColor).where(
            VehicleModelColor.vehicle_model_id == payload.vehicle_model_id,
            VehicleModelColor.color_id == payload.color_id,
            VehicleModelColor.is_active.is_(True),
        )
    ):
        raise HTTPException(status_code=422, detail="工厂-车型或车型-颜色关系未启用")
    existing = db.scalar(
        select(ModelApplicabilityScope).where(
            ModelApplicabilityScope.model_version_id == model.id,
            ModelApplicabilityScope.factory_id == payload.factory_id,
            ModelApplicabilityScope.vehicle_model_id == payload.vehicle_model_id,
            ModelApplicabilityScope.color_id == payload.color_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="该模型适用上下文已存在")
    scope = ModelApplicabilityScope(
        model_version_id=model.id,
        factory_id=payload.factory_id,
        vehicle_model_id=payload.vehicle_model_id,
        color_id=payload.color_id,
        status="PENDING",
        source="MANUAL",
        remark=payload.remark,
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope


def update_model_applicability_scope(db: Session, model: ModelVersion, scope, payload):
    scope.status = payload.status
    scope.remark = payload.remark
    if payload.status != "ACTIVE":
        scope.approved_by = None
        scope.approved_at = None
    if model.status == "ACTIVE" and not db.scalar(
        select(ModelApplicabilityScope).where(
            ModelApplicabilityScope.model_version_id == model.id,
            ModelApplicabilityScope.status == "ACTIVE",
            ModelApplicabilityScope.id != scope.id,
        )
    ):
        model.status = "RETIRED"
    db.commit()
    db.refresh(scope)
    return scope


def update_model_ood_policy(db: Session, model: ModelVersion, payload) -> ModelOodPolicy:
    policy = db.scalar(select(ModelOodPolicy).where(ModelOodPolicy.model_version_id == model.id))
    if not policy:
        policy = ModelOodPolicy(model_version_id=model.id)
        db.add(policy)
    policy.max_abs_standardized_shift = payload.max_abs_standardized_shift
    policy.max_outlier_feature_ratio = payload.max_outlier_feature_ratio
    policy.min_feature_completeness = payload.min_feature_completeness
    policy.action = payload.action
    policy.status = "PENDING"
    policy.approved_by = None
    policy.approved_at = None
    policy.remark = payload.remark
    if model.status == "ACTIVE":
        model.status = "RETIRED"
    db.commit()
    db.refresh(policy)
    return policy


def create_model_acceptance_policy(db: Session, payload) -> ModelAcceptancePolicy:
    _target_family(payload.target_metric)
    if not db.get(Factory, payload.factory_id):
        raise HTTPException(status_code=422, detail="验收策略引用的工厂不存在")
    if db.scalar(
        select(ModelAcceptancePolicy).where(
            ModelAcceptancePolicy.policy_code == payload.policy_code,
            ModelAcceptancePolicy.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="验收策略代码与版本已存在")
    policy = ModelAcceptancePolicy(
        policy_code=payload.policy_code,
        version=payload.version,
        factory_id=payload.factory_id,
        target_metric=payload.target_metric,
        policy_type="FACTORY_APPROVED",
        max_validation_rmse=payload.max_validation_rmse,
        min_validation_r2=payload.min_validation_r2,
        min_train_groups=payload.min_train_groups,
        min_validation_groups=payload.min_validation_groups,
        status="DRAFT",
        source_uri=payload.source_uri,
        remark=payload.remark,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_model_acceptance_policy_status(
    db: Session, policy: ModelAcceptancePolicy, payload
) -> ModelAcceptancePolicy:
    if payload.status == "ACTIVE" and not payload.approved_by:
        raise HTTPException(status_code=422, detail="激活工厂验收策略必须记录批准人")
    if payload.status == "ACTIVE":
        for active_policy in db.scalars(
            select(ModelAcceptancePolicy).where(
                ModelAcceptancePolicy.factory_id == policy.factory_id,
                ModelAcceptancePolicy.target_metric == policy.target_metric,
                ModelAcceptancePolicy.policy_type == policy.policy_type,
                ModelAcceptancePolicy.status == "ACTIVE",
                ModelAcceptancePolicy.id != policy.id,
            )
        ):
            active_policy.status = "RETIRED"
        policy.approved_by = payload.approved_by
        policy.approved_at = datetime.now(UTC)
    else:
        policy.approved_by = None
        policy.approved_at = None
    policy.status = payload.status
    for model in db.scalars(
        select(ModelVersion)
        .join(ModelApplicabilityScope, ModelApplicabilityScope.model_version_id == ModelVersion.id)
        .where(
            ModelVersion.target_metric == policy.target_metric,
            ModelVersion.status == "ACTIVE",
            ModelApplicabilityScope.factory_id == policy.factory_id,
            ModelApplicabilityScope.status == "ACTIVE",
        )
    ):
        model.status = "RETIRED"
    db.commit()
    db.refresh(policy)
    return policy


def _factory_acceptance_evidence(
    db: Session,
    model: ModelVersion,
    scopes: list[ModelApplicabilityScope] | None = None,
) -> dict:
    if scopes is None:
        scopes = list(
            db.scalars(
                select(ModelApplicabilityScope).where(
                    ModelApplicabilityScope.model_version_id == model.id,
                    ModelApplicabilityScope.status != "INACTIVE",
                )
            )
    )
    dataset = db.get(DatasetSnapshot, model.dataset_snapshot_id) if model.dataset_snapshot_id else None
    allowed_types = ["FACTORY_APPROVED"]
    details = []
    for factory_id in sorted({scope.factory_id for scope in scopes}):
        policy = db.scalar(
            select(ModelAcceptancePolicy)
            .where(
                ModelAcceptancePolicy.factory_id == factory_id,
                ModelAcceptancePolicy.target_metric == model.target_metric,
                ModelAcceptancePolicy.policy_type.in_(allowed_types),
                ModelAcceptancePolicy.status == "ACTIVE",
            )
            .order_by(
                ModelAcceptancePolicy.approved_at.desc(),
                ModelAcceptancePolicy.created_at.desc(),
            )
        )
        if not policy:
            details.append(
                {
                    "factory_id": factory_id,
                    "policy_id": None,
                    "policy_code": None,
                    "policy_type": None,
                    "checks_passed": False,
                    "checks": {"policy_present": False},
                }
            )
            continue
        metrics = model.evaluation_metrics
        validation_evidence = _multi_axis_validation_evidence(model)
        checks = {
            "policy_present": True,
            "validation_rmse": (
                metrics.get("validation_rmse") is not None
                and metrics["validation_rmse"] <= policy.max_validation_rmse
            ),
            "validation_r2": (
                metrics.get("validation_r2") is not None
                and metrics["validation_r2"] >= policy.min_validation_r2
            ),
            "train_group_count": (
                dataset is not None and dataset.train_group_count >= policy.min_train_groups
            ),
            "validation_group_count": (
                dataset is not None
                and dataset.validation_group_count >= policy.min_validation_groups
            ),
            "available_axis_rmse": (
                validation_evidence["worst_rmse"] is None
                or validation_evidence["worst_rmse"] <= policy.max_validation_rmse
            ),
            "available_axis_r2": (
                validation_evidence["worst_r2"] is None
                or validation_evidence["worst_r2"] >= policy.min_validation_r2
            ),
        }
        details.append(
            {
                "factory_id": factory_id,
                "policy_id": policy.id,
                "policy_code": f"{policy.policy_code}:{policy.version}",
                "policy_type": policy.policy_type,
                "source_uri": policy.source_uri,
                "thresholds": {
                    "max_validation_rmse": policy.max_validation_rmse,
                    "min_validation_r2": policy.min_validation_r2,
                    "min_train_groups": policy.min_train_groups,
                    "min_validation_groups": policy.min_validation_groups,
                },
                "multi_axis_validation": {
                    "evaluated_axis_count": validation_evidence["evaluated_axis_count"],
                    "insufficient_axes": validation_evidence["insufficient_axes"],
                    "worst_rmse": validation_evidence["worst_rmse"],
                    "worst_r2": validation_evidence["worst_r2"],
                },
                "checks_passed": all(checks.values()),
                "checks": checks,
            }
        )
    return {
        "policies_present": bool(details) and all(
            detail["checks"].get("policy_present", False) for detail in details
        ),
        "thresholds_passed": bool(details) and all(
            detail["checks_passed"] for detail in details
        ),
        "details": details,
    }


def build_dataset_snapshot(db: Session, payload) -> DatasetSnapshot:
    try:
        require_scope_safe_model(payload.target_metric, payload.feature_set_version, [])
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if db.scalar(
        select(DatasetSnapshot).where(
            DatasetSnapshot.dataset_code == payload.dataset_code,
            DatasetSnapshot.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="数据集代码与版本已存在")

    production_query = (
        select(PointFeatureSnapshot, ProductionRun)
        .join(ProductionRun, ProductionRun.id == PointFeatureSnapshot.production_run_id)
        .where(
            PointFeatureSnapshot.feature_set_version == payload.feature_set_version,
            PointFeatureSnapshot.target_family == _target_family(payload.target_metric),
        )
    )
    if not payload.include_all_production:
        if payload.production_snapshot_ids:
            production_query = production_query.where(
                PointFeatureSnapshot.id.in_(payload.production_snapshot_ids)
            )
        else:
            production_query = production_query.where(PointFeatureSnapshot.id == "")
    elif payload.production_snapshot_ids:
        production_query = production_query.where(
            PointFeatureSnapshot.id.in_(payload.production_snapshot_ids)
        )
    rows = db.execute(
        production_query.order_by(
            ProductionRun.started_at, PointFeatureSnapshot.measurement_point_id
        )
    ).all()
    candidates: list[dict] = []
    for snapshot, run in rows:
        target_observation = _target_observation(
            db, snapshot.production_run_id, snapshot.measurement_point_id, payload.target_metric
        )
        features = approved_numeric_values(snapshot.feature_values)
        if target_observation is None or not features:
            continue
        group_value = (
            f"body:{run.factory_id}:{run.body_no}"
            if run.body_no
            else f"run:{run.run_no}"
        )
        candidates.append(
            {
                "source_type": "PRODUCTION",
                "source_ref": f"P:{snapshot.id}",
                "snapshot": snapshot,
                "run": run,
                "manual_sample": None,
                "target": float(target_observation["value"]),
                "target_measurement_id": target_observation["measurement_id"],
                "features": features,
                "group_value": group_value,
                "occurred_at": run.started_at,
            }
        )

    selected_uploads: list[TrainingDataUpload] = []
    if payload.manual_upload_ids:
        selected_uploads = list(
            db.scalars(
                select(TrainingDataUpload).where(
                    TrainingDataUpload.id.in_(payload.manual_upload_ids)
                )
            )
        )
        found_ids = {upload.id for upload in selected_uploads}
        missing_ids = sorted(set(payload.manual_upload_ids) - found_ids)
        if missing_ids:
            raise HTTPException(status_code=404, detail="所选人工训练数据文件不存在")
        incompatible = [
            upload.name
            for upload in selected_uploads
            if upload.status != "VALIDATED"
            or upload.target_metric != payload.target_metric
            or upload.feature_set_version != payload.feature_set_version
        ]
        if incompatible:
            raise HTTPException(
                status_code=422,
                detail=f"以下人工训练数据与目标指标或特征版本不一致：{', '.join(incompatible)}",
            )
        manual_rows = list(
            db.scalars(
                select(TrainingWideSample)
                .where(
                    TrainingWideSample.upload_id.in_(payload.manual_upload_ids),
                    TrainingWideSample.is_valid.is_(True),
                )
                .order_by(TrainingWideSample.occurred_at, TrainingWideSample.sample_no)
            )
        )
        for sample in manual_rows:
            features = approved_numeric_values(sample.feature_values)
            if not features:
                continue
            candidates.append(
                {
                    "source_type": "MANUAL_UPLOAD",
                    "source_ref": f"M:{sample.id}",
                    "snapshot": None,
                    "run": None,
                    "manual_sample": sample,
                    "target": float(sample.target_value),
                    "target_measurement_id": None,
                    "features": features,
                    "group_value": f"manual:{sample.group_value}",
                    "occurred_at": sample.occurred_at,
                }
            )
    groups: dict[str, list[dict]] = {}
    for candidate in candidates:
        groups.setdefault(candidate["group_value"], []).append(candidate)
    if not candidates:
        raise HTTPException(
            status_code=422,
            detail=(
                "没有可用训练样本；请选择生产样本或已通过校验的人工训练数据文件。"
                "两种来源可以单独使用或混合使用"
            ),
        )
    ordered_groups = sorted(
        groups,
        key=lambda group: min(_time_key(item["occurred_at"]) for item in groups[group]),
    )
    required_groups = payload.min_train_groups + payload.min_validation_groups
    if len(ordered_groups) < required_groups:
        raise HTTPException(
            status_code=422,
            detail=(
                f"独立数据分组不足：训练至少 {payload.min_train_groups} 组、"
                f"验证至少 {payload.min_validation_groups} 组，当前 {len(ordered_groups)} 组"
            ),
        )
    validation_group_count = max(
        payload.min_validation_groups,
        ceil(len(ordered_groups) * payload.holdout_ratio),
    )
    validation_group_count = min(
        validation_group_count,
        len(ordered_groups) - payload.min_train_groups,
    )
    validation_groups = set(ordered_groups[-validation_group_count:])
    train_groups = set(ordered_groups) - validation_groups

    common_features = set(candidates[0]["features"])
    for candidate in candidates[1:]:
        common_features &= set(candidate["features"])
    feature_names = sorted(common_features)
    if not feature_names:
        raise HTTPException(status_code=422, detail="数据集样本没有共同数值特征")

    train_rows = [item for item in candidates if item["group_value"] in train_groups]
    validation_rows = [item for item in candidates if item["group_value"] in validation_groups]
    train_source_refs = {item["source_ref"] for item in train_rows}
    validation_source_refs = {item["source_ref"] for item in validation_rows}
    leakage_check = {
        "group_overlap_count": len(train_groups & validation_groups),
        "snapshot_overlap_count": len(train_source_refs & validation_source_refs),
        "temporal_order_valid": max(_time_key(item["occurred_at"]) for item in train_rows)
        <= min(_time_key(item["occurred_at"]) for item in validation_rows),
    }
    leakage_check["passed"] = (
        leakage_check["group_overlap_count"] == 0
        and leakage_check["snapshot_overlap_count"] == 0
        and leakage_check["temporal_order_valid"]
    )
    if not leakage_check["passed"]:
        raise HTTPException(
            status_code=422,
            detail="分组跨越时间切分边界，数据集未通过泄漏检查",
        )
    now = datetime.now(UTC)
    dataset = DatasetSnapshot(
        dataset_code=payload.dataset_code,
        version=payload.version,
        target_metric=payload.target_metric,
        feature_set_version=payload.feature_set_version,
        split_strategy="TEMPORAL_GROUPED_HOLDOUT",
        group_key="BODY_RUN_OR_MANUAL_GROUP",
        holdout_ratio=payload.holdout_ratio,
        status="BUILT",
        sample_count=len(candidates),
        group_count=len(groups),
        train_sample_count=len(train_rows),
        validation_sample_count=len(validation_rows),
        train_group_count=len(train_groups),
        validation_group_count=len(validation_groups),
        cutoff_at=min(
            validation_rows, key=lambda item: _time_key(item["occurred_at"])
        )["occurred_at"],
        feature_names=feature_names,
        lineage={
            "source_policy": "PRODUCTION_AND_MANUAL_EQUAL_WEIGHT",
            "source_counts": {
                "PRODUCTION": sum(
                    item["source_type"] == "PRODUCTION" for item in candidates
                ),
                "MANUAL_UPLOAD": sum(
                    item["source_type"] == "MANUAL_UPLOAD" for item in candidates
                ),
            },
            "point_feature_snapshot_ids": [
                item["snapshot"].id for item in candidates if item["snapshot"]
            ],
            "manual_upload_ids": [upload.id for upload in selected_uploads],
            "manual_sample_ids": [
                item["manual_sample"].id
                for item in candidates
                if item["manual_sample"]
            ],
            "production_run_ids": sorted(
                {item["run"].id for item in candidates if item["run"]}
            ),
            "target_measurement_ids": [
                item["target_measurement_id"]
                for item in candidates
                if item["target_measurement_id"]
            ],
            "production_target_reliability_status": "VERIFIED",
            "manual_data_validation_status": "VALIDATED",
        },
        leakage_check=leakage_check,
        built_at=now,
    )
    db.add(dataset)
    db.flush()
    for item in candidates:
        db.add(
            DatasetSplitMember(
                dataset_snapshot_id=dataset.id,
                source_type=item["source_type"],
                source_ref=item["source_ref"],
                point_feature_snapshot_id=(
                    item["snapshot"].id if item["snapshot"] else None
                ),
                manual_sample_id=(
                    item["manual_sample"].id if item["manual_sample"] else None
                ),
                production_run_id=item["run"].id if item["run"] else None,
                measurement_point_id=(
                    item["snapshot"].measurement_point_id if item["snapshot"] else None
                ),
                target_measurement_id=item["target_measurement_id"],
                group_value=item["group_value"],
                split="VALIDATION" if item["group_value"] in validation_groups else "TRAIN",
                target_value=item["target"],
                feature_values={name: item["features"][name] for name in feature_names},
                occurred_at=item["occurred_at"],
            )
        )
    db.commit()
    db.refresh(dataset)
    return dataset


def train_model(db: Session, payload) -> ModelVersion:
    try:
        require_scope_safe_model(payload.target_metric, payload.feature_set_version, [])
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_code == payload.model_code,
            ModelVersion.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="模型代码与版本已存在")

    dataset = db.get(DatasetSnapshot, payload.dataset_snapshot_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="训练数据集快照不存在")
    if (
        dataset.target_metric != payload.target_metric
        or dataset.feature_set_version != payload.feature_set_version
    ):
        raise HTTPException(status_code=422, detail="模型目标或特征版本与数据集不一致")
    if not dataset.leakage_check.get("passed"):
        raise HTTPException(status_code=422, detail="数据集未通过分组与时间泄漏检查")
    members = list(
        db.scalars(
            select(DatasetSplitMember).where(
                DatasetSplitMember.dataset_snapshot_id == dataset.id,
            )
        )
    )
    train_members = [member for member in members if member.split == "TRAIN"]
    validation_members = [member for member in members if member.split == "VALIDATION"]
    train_samples = [
        (member.feature_values, member.target_value) for member in train_members
    ]
    validation_samples = [
        (member.feature_values, member.target_value) for member in validation_members
    ]
    if len(train_samples) < payload.min_samples:
        raise HTTPException(
            status_code=422,
            detail=f"有效训练样本不足：需要 {payload.min_samples}，当前 {len(train_samples)}",
        )
    if not validation_samples:
        raise HTTPException(status_code=422, detail="数据集没有独立验证样本")

    fitted, model_selection = _select_training_model(
        train_members,
        payload.model_family,
        payload.ridge_lambda,
        payload.elastic_net_l1_ratio,
    )
    try:
        require_scope_safe_model(
            payload.target_metric,
            payload.feature_set_version,
            fitted["feature_names"],
        )
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    validation_predictions = _predict_samples(fitted, validation_samples)
    validation_metrics = _regression_metrics(
        validation_predictions,
        [target for _features, target in validation_samples],
        "validation",
    )
    fitted["residual_std"] = validation_metrics["validation_rmse"]
    fitted["uncertainty_source"] = "TEMPORAL_VALIDATION_RMSE"
    evaluation_metrics = {
        **fitted["evaluation_metrics"],
        **validation_metrics,
        "train_group_count": dataset.train_group_count,
        "validation_group_count": dataset.validation_group_count,
        "leakage_check_passed": dataset.leakage_check.get("passed", False),
        "model_selection": model_selection,
    }
    now = datetime.now(UTC)
    model = ModelVersion(
        model_code=payload.model_code,
        version=payload.version,
        model_type=(
            "ELASTIC_NET_REGRESSION"
            if fitted["model_family"] == "ELASTIC_NET"
            else "RIDGE_REGRESSION"
        ),
        target_metric=payload.target_metric,
        feature_set_version=payload.feature_set_version,
        artifact_uri=f"mysql://model-version/{payload.model_code}/{payload.version}",
        dataset_snapshot_id=dataset.id,
        model_payload={
            key: value for key, value in fitted.items() if key != "evaluation_metrics"
        },
        evaluation_metrics=evaluation_metrics,
        training_sample_count=len(train_samples),
        trained_at=now,
        status="DRAFT",
    )
    db.add(model)
    db.flush()
    multi_axis_validation = _create_validation_folds(
        db,
        model,
        dataset,
        model_config=model_selection["selected"],
        min_train_samples=payload.min_samples,
        time_holdout_metrics=validation_metrics,
    )
    model.evaluation_metrics = {
        **model.evaluation_metrics,
        "multi_axis_validation": multi_axis_validation,
    }
    ensure_model_governance(
        db,
        model,
        max_abs_standardized_shift=payload.max_abs_standardized_shift,
        max_outlier_feature_ratio=payload.max_outlier_feature_ratio,
        min_feature_completeness=payload.min_feature_completeness,
    )
    _register_model_artifact(db, model)
    db.commit()
    db.refresh(model)
    return model


def record_model_acceptance(db: Session, model: ModelVersion, payload) -> ModelAcceptanceDecision:
    if not model.dataset_snapshot_id:
        raise HTTPException(status_code=409, detail="旧模型没有受治理的数据集快照，不能验收")
    dataset = db.get(DatasetSnapshot, model.dataset_snapshot_id)
    scopes = list(
        db.scalars(
            select(ModelApplicabilityScope).where(
                ModelApplicabilityScope.model_version_id == model.id,
                ModelApplicabilityScope.status != "INACTIVE",
            )
        )
    )
    policy = db.scalar(select(ModelOodPolicy).where(ModelOodPolicy.model_version_id == model.id))
    factory_acceptance = _factory_acceptance_evidence(db, model, scopes)
    validation_evidence = _multi_axis_validation_evidence(model)
    artifact_evidence = _model_artifact_evidence(db, model)
    leakage_passed = bool(dataset and dataset.leakage_check.get("passed"))
    metrics = model.evaluation_metrics
    threshold_checks = {
        "max_validation_rmse": (
            payload.max_validation_rmse is None
            or metrics.get("validation_rmse") <= payload.max_validation_rmse
        ),
        "min_validation_r2": (
            payload.min_validation_r2 is None
            or metrics.get("validation_r2") >= payload.min_validation_r2
        ),
    }
    checks = {
        "dataset_exists": dataset is not None,
        "leakage_check_passed": leakage_passed,
        "has_independent_validation": bool(dataset and dataset.validation_group_count > 0),
        "has_configured_applicability_scope": bool(scopes),
        "has_configured_ood_policy": policy is not None and policy.action == "BLOCK",
        "has_multi_axis_validation_report": validation_evidence["report_present"],
        "has_evaluated_validation_axis": validation_evidence["evaluated_axis_count"] > 0,
        "has_registered_model_artifact": artifact_evidence["registered"],
        "model_artifact_hash_matches": artifact_evidence["hash_matches"],
        "factory_acceptance_policies_present": factory_acceptance["policies_present"],
        "factory_acceptance_thresholds_passed": factory_acceptance["thresholds_passed"],
        **threshold_checks,
    }
    checks["all_required_checks_passed"] = all(checks.values())
    if payload.decision == "ACCEPTED" and not checks["all_required_checks_passed"]:
        failed_checks = [
            name for name, passed in checks.items() if name != "all_required_checks_passed" and not passed
        ]
        raise HTTPException(
            status_code=422,
            detail=f"模型未满足验收检查，不能记录为通过：{', '.join(failed_checks)}",
        )
    decision = ModelAcceptanceDecision(
        model_version_id=model.id,
        dataset_snapshot_id=model.dataset_snapshot_id,
        decision=payload.decision,
        criteria={
            "max_validation_rmse": payload.max_validation_rmse,
            "min_validation_r2": payload.min_validation_r2,
            "factory_acceptance_policies": factory_acceptance["details"],
            "multi_axis_validation": validation_evidence,
            "model_artifact": artifact_evidence,
        },
        checks=checks,
        decided_by=payload.decided_by,
        decided_at=datetime.now(UTC),
        comment=payload.comment,
    )
    if payload.decision == "REJECTED" and model.status == "ACTIVE":
        model.status = "RETIRED"
    if payload.decision == "ACCEPTED":
        approved_at = datetime.now(UTC)
        for scope in scopes:
            scope.status = "ACTIVE"
            scope.approved_by = payload.decided_by
            scope.approved_at = approved_at
        policy.status = "ACTIVE"
        policy.approved_by = payload.decided_by
        policy.approved_at = approved_at
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def model_drift_report(db: Session, model: ModelVersion, recent_limit: int = 100) -> dict:
    payload = model.model_payload
    feature_names = payload.get("feature_names", [])
    means = payload.get("means", [])
    scales = payload.get("scales", [])
    snapshots = list(
        db.scalars(
            select(PointFeatureSnapshot)
            .where(
                PointFeatureSnapshot.feature_set_version == model.feature_set_version,
                PointFeatureSnapshot.target_family == _target_family(model.target_metric),
            )
            .order_by(PointFeatureSnapshot.generated_at.desc())
            .limit(recent_limit)
        )
    )
    predictions = list(
        db.scalars(
            select(PredictionResult)
            .where(PredictionResult.model_version_id == model.id)
            .order_by(PredictionResult.predicted_at.desc())
            .limit(recent_limit)
        )
    )

    feature_drift = []
    for feature_name, training_mean, training_scale in zip(
        feature_names, means, scales, strict=True
    ):
        values = [
            float(snapshot.feature_values[feature_name])
            for snapshot in snapshots
            if isinstance(snapshot.feature_values.get(feature_name), int | float)
            and not isinstance(snapshot.feature_values.get(feature_name), bool)
        ]
        recent_mean = sum(values) / len(values) if values else None
        mean_shift = (
            abs(recent_mean - float(training_mean)) / (abs(float(training_scale)) or 1.0)
            if recent_mean is not None
            else None
        )
        missing_rate = 1 - len(values) / len(snapshots) if snapshots else 1.0
        if mean_shift is None:
            drift_status = "NO_DATA"
        elif mean_shift >= 1.0 or missing_rate >= 0.2:
            drift_status = "DRIFT"
        elif mean_shift >= 0.5 or missing_rate >= 0.05:
            drift_status = "WATCH"
        else:
            drift_status = "STABLE"
        feature_drift.append(
            {
                "feature": feature_name,
                "training_mean": round(float(training_mean), 6),
                "recent_mean": round(recent_mean, 6) if recent_mean is not None else None,
                "standardized_mean_shift": round(mean_shift, 6) if mean_shift is not None else None,
                "missing_rate": round(missing_rate, 6),
                "sample_count": len(values),
                "status": drift_status,
            }
        )
    feature_drift.sort(
        key=lambda item: (
            item["standardized_mean_shift"] is not None,
            item["standardized_mean_shift"] or 0,
            item["missing_rate"],
        ),
        reverse=True,
    )

    errors = []
    for prediction in predictions:
        actual = _target_value(
            db,
            prediction.production_run_id,
            prediction.measurement_point_id,
            prediction.metric_code,
        )
        if actual is not None:
            errors.append(prediction.predicted_value - actual)
    live_mae = sum(abs(error) for error in errors) / len(errors) if errors else None
    live_rmse = sqrt(sum(error**2 for error in errors) / len(errors)) if errors else None
    training_rmse = model.evaluation_metrics.get("training_rmse")
    validation_rmse = model.evaluation_metrics.get("validation_rmse")
    baseline_rmse = validation_rmse if validation_rmse is not None else training_rmse
    baseline_source = "VALIDATION" if validation_rmse is not None else "TRAINING_LEGACY"
    rmse_ratio = (
        live_rmse / float(baseline_rmse)
        if live_rmse is not None and baseline_rmse is not None and float(baseline_rmse) > 0
        else None
    )
    max_feature_shift = max(
        (
            item["standardized_mean_shift"]
            for item in feature_drift
            if item["standardized_mean_shift"] is not None
        ),
        default=None,
    )
    average_completeness = (
        sum(
            sum(name in snapshot.feature_values for name in feature_names) / len(feature_names)
            for snapshot in snapshots
        )
        / len(snapshots)
        if snapshots and feature_names
        else None
    )
    average_confidence = (
        sum(prediction.confidence for prediction in predictions) / len(predictions)
        if predictions
        else None
    )
    has_feature_drift = any(item["status"] == "DRIFT" for item in feature_drift)
    has_feature_watch = any(item["status"] == "WATCH" for item in feature_drift)
    has_effect_drift = rmse_ratio is not None and rmse_ratio >= 1.5
    has_effect_watch = rmse_ratio is not None and rmse_ratio >= 1.2

    if not snapshots:
        drift_status = "NO_DATA"
        recommendation = "当前没有可用于漂移监控的点位特征快照，请先接入最新生产数据。"
    elif has_feature_drift or has_effect_drift:
        drift_status = "DRIFT"
        recommendation = "检测到显著特征或效果漂移，建议暂停自动推荐并使用最新合格数据重新训练。"
    elif has_feature_watch or has_effect_watch or not errors:
        drift_status = "WATCH"
        recommendation = "模型需要持续观察，请补充带质量结果的在线样本并复核高漂移特征。"
    else:
        drift_status = "STABLE"
        recommendation = "模型输入分布与在线效果稳定，可继续按当前治理策略运行。"

    return {
        "model_version_id": model.id,
        "model_code": model.model_code,
        "version": model.version,
        "target_metric": model.target_metric,
        "model_status": model.status,
        "drift_status": drift_status,
        "recommendation": recommendation,
        "monitored_snapshot_count": len(snapshots),
        "prediction_count": len(predictions),
        "labeled_prediction_count": len(errors),
        "average_feature_completeness": (
            round(average_completeness, 6) if average_completeness is not None else None
        ),
        "average_confidence": (
            round(average_confidence, 6) if average_confidence is not None else None
        ),
        "training_rmse": round(float(training_rmse), 6) if training_rmse is not None else None,
        "validation_rmse": (
            round(float(validation_rmse), 6) if validation_rmse is not None else None
        ),
        "baseline_rmse": round(float(baseline_rmse), 6) if baseline_rmse is not None else None,
        "baseline_source": baseline_source,
        "live_mae": round(live_mae, 6) if live_mae is not None else None,
        "live_rmse": round(live_rmse, 6) if live_rmse is not None else None,
        "rmse_ratio": round(rmse_ratio, 6) if rmse_ratio is not None else None,
        "max_feature_shift": (
            round(max_feature_shift, 6) if max_feature_shift is not None else None
        ),
        "window_started_at": min(
            (snapshot.generated_at for snapshot in snapshots), default=None
        ),
        "window_ended_at": max(
            (snapshot.generated_at for snapshot in snapshots), default=None
        ),
        "feature_drift": feature_drift,
    }


def update_model_status(db: Session, model: ModelVersion, next_status: str) -> ModelVersion:
    if next_status == "ACTIVE":
        _ensure_model_scope(model)
        acceptance = db.scalar(
            select(ModelAcceptanceDecision)
            .where(ModelAcceptanceDecision.model_version_id == model.id)
            .order_by(ModelAcceptanceDecision.decided_at.desc())
        )
        if (
            not acceptance
            or acceptance.decision != "ACCEPTED"
            or not acceptance.checks.get("all_required_checks_passed")
        ):
            raise HTTPException(status_code=409, detail="模型必须先通过独立验证和人工验收才能激活")
        if not db.scalar(
            select(ModelApplicabilityScope).where(
                ModelApplicabilityScope.model_version_id == model.id,
                ModelApplicabilityScope.status == "ACTIVE",
            )
        ):
            raise HTTPException(status_code=409, detail="模型没有已批准的适用范围，不能激活")
        policy = db.scalar(
            select(ModelOodPolicy).where(
                ModelOodPolicy.model_version_id == model.id,
                ModelOodPolicy.status == "ACTIVE",
            )
        )
        if not policy or policy.action != "BLOCK":
            raise HTTPException(status_code=409, detail="模型没有已批准的 OOD 阻断策略，不能激活")
        validation_evidence = _multi_axis_validation_evidence(model)
        if (
            not validation_evidence["report_present"]
            or validation_evidence["evaluated_axis_count"] <= 0
        ):
            raise HTTPException(status_code=409, detail="模型没有多维验证折报告，不能激活")
        artifact_evidence = _model_artifact_evidence(db, model)
        if not artifact_evidence["registered"] or not artifact_evidence["hash_matches"]:
            raise HTTPException(status_code=409, detail="模型工件未登记或哈希不匹配，不能激活")
        factory_acceptance = _factory_acceptance_evidence(db, model)
        if not factory_acceptance["policies_present"]:
            raise HTTPException(status_code=409, detail="模型全部适用工厂必须配置生效验收策略")
        if not factory_acceptance["thresholds_passed"]:
            raise HTTPException(status_code=409, detail="模型未满足当前生效的工厂验收阈值")
        new_contexts = set(
            db.execute(
                select(
                    ModelApplicabilityScope.factory_id,
                    ModelApplicabilityScope.vehicle_model_id,
                    ModelApplicabilityScope.color_id,
                ).where(
                    ModelApplicabilityScope.model_version_id == model.id,
                    ModelApplicabilityScope.status == "ACTIVE",
                )
            ).all()
        )
        for active_model in db.scalars(
            select(ModelVersion).where(
                ModelVersion.target_metric == model.target_metric,
                ModelVersion.status == "ACTIVE",
                ModelVersion.id != model.id,
            )
        ):
            active_contexts = set(
                db.execute(
                    select(
                        ModelApplicabilityScope.factory_id,
                        ModelApplicabilityScope.vehicle_model_id,
                        ModelApplicabilityScope.color_id,
                    ).where(
                        ModelApplicabilityScope.model_version_id == active_model.id,
                        ModelApplicabilityScope.status == "ACTIVE",
                    )
                ).all()
            )
            if new_contexts & active_contexts:
                active_model.status = "RETIRED"
    model.status = next_status
    db.commit()
    db.refresh(model)
    return model


def model_governance_check(
    db: Session,
    model: ModelVersion,
    production_run_id: str,
    measurement_point_id: str,
) -> dict:
    _ensure_model_scope(model)
    run = db.get(ProductionRun, production_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="生产事件不存在")
    snapshot = db.scalar(
        select(PointFeatureSnapshot).where(
            PointFeatureSnapshot.production_run_id == production_run_id,
            PointFeatureSnapshot.measurement_point_id == measurement_point_id,
            PointFeatureSnapshot.feature_set_version == model.feature_set_version,
            PointFeatureSnapshot.target_family == _target_family(model.target_metric),
        )
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="未找到与模型特征版本匹配的点位特征快照")
    scope = db.scalar(
        select(ModelApplicabilityScope).where(
            ModelApplicabilityScope.model_version_id == model.id,
            ModelApplicabilityScope.factory_id == run.factory_id,
            ModelApplicabilityScope.vehicle_model_id == run.vehicle_model_id,
            ModelApplicabilityScope.color_id == run.color_id,
            ModelApplicabilityScope.status == "ACTIVE",
        )
    )
    policy = db.scalar(
        select(ModelOodPolicy).where(
            ModelOodPolicy.model_version_id == model.id,
            ModelOodPolicy.status == "ACTIVE",
        )
    )
    payload = model.model_payload
    feature_names = payload.get("feature_names", [])
    missing_features = [
        name
        for name in feature_names
        if not isinstance(snapshot.feature_values.get(name), int | float)
        or isinstance(snapshot.feature_values.get(name), bool)
    ]
    feature_completeness = (
        (len(feature_names) - len(missing_features)) / len(feature_names)
        if feature_names
        else 0.0
    )
    feature_shifts = []
    for name, mean, scale in zip(
        feature_names,
        payload.get("means", []),
        payload.get("scales", []),
        strict=True,
    ):
        value = snapshot.feature_values.get(name)
        if name in missing_features:
            continue
        shift = abs(float(value) - float(mean)) / (abs(float(scale)) or 1.0)
        feature_shifts.append(
            {
                "feature": name,
                "value": float(value),
                "standardized_shift": round(shift, 6),
            }
        )
    max_shift = max((item["standardized_shift"] for item in feature_shifts), default=None)
    outlier_features = (
        [
            item
            for item in feature_shifts
            if item["standardized_shift"] > policy.max_abs_standardized_shift
        ]
        if policy
        else []
    )
    outlier_ratio = len(outlier_features) / len(feature_names) if feature_names else 1.0
    applicability_status = "IN_SCOPE" if scope else "OUT_OF_SCOPE"
    if not policy:
        ood_status = "POLICY_NOT_APPROVED"
    elif (
        feature_completeness < policy.min_feature_completeness
        or outlier_ratio > policy.max_outlier_feature_ratio
    ):
        ood_status = "OUT_OF_DISTRIBUTION"
    else:
        ood_status = "IN_DISTRIBUTION"
    allowed = applicability_status == "IN_SCOPE" and ood_status == "IN_DISTRIBUTION"
    evidence = {
        "scope_id": scope.id if scope else None,
        "policy_id": policy.id if policy else None,
        "context": {
            "factory_id": run.factory_id,
            "vehicle_model_id": run.vehicle_model_id,
            "color_id": run.color_id,
        },
        "feature_completeness": round(feature_completeness, 6),
        "missing_features": missing_features,
        "max_abs_standardized_shift": max_shift,
        "outlier_feature_ratio": round(outlier_ratio, 6),
        "outlier_features": outlier_features,
        "policy": (
            {
                "max_abs_standardized_shift": policy.max_abs_standardized_shift,
                "max_outlier_feature_ratio": policy.max_outlier_feature_ratio,
                "min_feature_completeness": policy.min_feature_completeness,
                "action": policy.action,
            }
            if policy
            else None
        ),
    }
    return {
        "model_version_id": model.id,
        "production_run_id": production_run_id,
        "measurement_point_id": measurement_point_id,
        "allowed": allowed,
        "applicability_status": applicability_status,
        "ood_status": ood_status,
        "evidence": evidence,
        "_snapshot": snapshot,
    }


def available_models_for_point(
    db: Session,
    production_run_id: str,
    measurement_point_id: str,
    target_metric: str | None = None,
) -> list[dict]:
    run = db.get(ProductionRun, production_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="生产事件不存在")
    models = list(
        db.scalars(
            select(ModelVersion)
            .join(
                ModelApplicabilityScope,
                ModelApplicabilityScope.model_version_id == ModelVersion.id,
            )
            .where(
                ModelVersion.status == "ACTIVE",
                ModelApplicabilityScope.factory_id == run.factory_id,
                ModelApplicabilityScope.vehicle_model_id == run.vehicle_model_id,
                ModelApplicabilityScope.color_id == run.color_id,
                ModelApplicabilityScope.status == "ACTIVE",
            )
            .order_by(ModelVersion.target_metric, ModelVersion.trained_at.desc())
        )
    )
    if target_metric:
        models = [model for model in models if model.target_metric == target_metric]
    metric_names = {
        definition.code: definition.name
        for definition in db.scalars(
            select(QualityMetricDefinition).where(
                QualityMetricDefinition.code.in_({model.target_metric for model in models})
            )
        )
    } if models else {}
    available = []
    for model in models:
        try:
            check = model_governance_check(
                db, model, production_run_id, measurement_point_id
            )
            available.append(
                {
                    "id": model.id,
                    "model_code": model.model_code,
                    "version": model.version,
                    "model_type": model.model_type,
                    "target_metric": model.target_metric,
                    "target_name": metric_names.get(model.target_metric, model.target_metric),
                    "allowed": check["allowed"],
                    "applicability_status": check["applicability_status"],
                    "ood_status": check["ood_status"],
                    "reason": None if check["allowed"] else "当前点位参数未通过模型使用检查",
                }
            )
        except HTTPException as exc:
            available.append(
                {
                    "id": model.id,
                    "model_code": model.model_code,
                    "version": model.version,
                    "model_type": model.model_type,
                    "target_metric": model.target_metric,
                    "target_name": metric_names.get(model.target_metric, model.target_metric),
                    "allowed": False,
                    "applicability_status": "IN_SCOPE",
                    "ood_status": "FEATURES_NOT_READY",
                    "reason": str(exc.detail),
                }
            )
    return sorted(available, key=lambda item: (not item["allowed"], item["target_metric"]))


def _require_governed_inference(check: dict) -> None:
    if check["allowed"]:
        return
    reasons = []
    if check["applicability_status"] != "IN_SCOPE":
        reasons.append("生产事件的工厂/车型/颜色不在模型已批准适用范围")
    if check["ood_status"] == "POLICY_NOT_APPROVED":
        reasons.append("模型没有已批准的 OOD 阻断策略")
    elif check["ood_status"] != "IN_DISTRIBUTION":
        evidence = check["evidence"]
        reasons.append(
            "输入分布外："
            f"完整率 {evidence['feature_completeness']:.1%}，"
            f"异常特征比例 {evidence['outlier_feature_ratio']:.1%}"
        )
    raise HTTPException(status_code=409, detail="；".join(reasons))


def predict_with_model(
    db: Session,
    model: ModelVersion,
    production_run_id: str,
    measurement_point_id: str,
    persist_result: bool = True,
) -> dict:
    _ensure_model_scope(model)
    governance = model_governance_check(
        db, model, production_run_id, measurement_point_id
    )
    _require_governed_inference(governance)
    snapshot = governance.pop("_snapshot")

    payload = model.model_payload
    feature_names = payload["feature_names"]
    present_count = sum(name in snapshot.feature_values for name in feature_names)
    normalized = [
        (float(snapshot.feature_values.get(name, mean)) - mean) / scale
        for name, mean, scale in zip(
            feature_names, payload["means"], payload["scales"], strict=True
        )
    ]
    predicted_value = payload["intercept"] + sum(
        coefficient * value
        for coefficient, value in zip(payload["coefficients"], normalized, strict=True)
    )
    residual_std = float(payload.get("residual_std", 0.0))
    feature_completeness = present_count / len(feature_names)
    max_shift = governance["evidence"].get("max_abs_standardized_shift") or 0.0
    policy = governance["evidence"].get("policy") or {}
    shift_limit = float(policy.get("max_abs_standardized_shift") or 4.0)
    distribution_support = max(0.2, 1 - min(1.0, float(max_shift) / shift_limit) * 0.5)
    sample_support = min(1.0, model.training_sample_count / 30)
    confidence = round(
        min(0.99, feature_completeness * distribution_support * (0.6 + 0.4 * sample_support)),
        4,
    )
    uncertainty_source = str(
        payload.get("uncertainty_source", "TRAINING_RESIDUAL_RMSE_LEGACY")
    )
    prediction = None
    if persist_result:
        prediction = PredictionResult(
            model_version_id=model.id,
            production_run_id=production_run_id,
            measurement_point_id=measurement_point_id,
            metric_code=model.target_metric,
            predicted_value=predicted_value,
            lower_bound=predicted_value - 1.96 * residual_std,
            upper_bound=predicted_value + 1.96 * residual_std,
            confidence=confidence,
            applicability_status=governance["applicability_status"],
            ood_status=governance["ood_status"],
            governance_evidence=governance["evidence"],
            predicted_at=datetime.now(UTC),
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
    return {
        "prediction_result_id": prediction.id if prediction else None,
        "model_version_id": model.id,
        "production_run_id": production_run_id,
        "measurement_point_id": measurement_point_id,
        "metric_code": model.target_metric,
        "model_type": model.model_type,
        "predicted_value": predicted_value,
        "lower_bound": predicted_value - 1.96 * residual_std,
        "upper_bound": predicted_value + 1.96 * residual_std,
        "confidence": confidence,
        "uncertainty_source": uncertainty_source,
        "feature_completeness": feature_completeness,
        "applicability_status": governance["applicability_status"],
        "ood_status": governance["ood_status"],
        "governance_evidence": governance["evidence"],
    }


def diagnose_prediction(db: Session, prediction: PredictionResult) -> DiagnosisResult:
    model = db.get(ModelVersion, prediction.model_version_id)
    _ensure_model_scope(model)
    if (
        prediction.applicability_status != "IN_SCOPE"
        or prediction.ood_status != "IN_DISTRIBUTION"
    ):
        raise HTTPException(status_code=409, detail="未通过适用范围与 OOD 门禁的预测不能生成诊断")
    snapshot = db.scalar(
        select(PointFeatureSnapshot).where(
            PointFeatureSnapshot.production_run_id == prediction.production_run_id,
            PointFeatureSnapshot.measurement_point_id == prediction.measurement_point_id,
            PointFeatureSnapshot.feature_set_version == model.feature_set_version,
            PointFeatureSnapshot.target_family == _target_family(model.target_metric),
        )
    )
    payload = model.model_payload
    contributions = []
    for name, mean, scale, coefficient in zip(
        payload["feature_names"],
        payload["means"],
        payload["scales"],
        payload["coefficients"],
        strict=True,
    ):
        value = float(snapshot.feature_values.get(name, mean))
        impact = coefficient * ((value - mean) / scale)
        contributions.append(
            {
                "feature": name,
                "value": value,
                "impact": impact,
                "direction": "positive" if impact >= 0 else "negative",
                "global_importance": abs(coefficient),
                "basis": "LOCAL_CONTRIBUTION",
            }
        )
    if contributions and max(abs(item["impact"]) for item in contributions) < 1e-9:
        for item in contributions:
            item["impact"] = item["global_importance"]
            item["direction"] = "global"
            item["basis"] = "GLOBAL_MODEL_WEIGHT"
    contributions.sort(key=lambda item: abs(item["impact"]), reverse=True)
    top_factors = contributions[:5]
    if top_factors and top_factors[0]["basis"] == "GLOBAL_MODEL_WEIGHT":
        summary = (
            f"当前特征接近训练均值，模型全局权重认为 {top_factors[0]['feature']} "
            f"与 {prediction.metric_code} 的关联最强。"
        )
    elif top_factors:
        summary = f"模型认为 {top_factors[0]['feature']} 对 {prediction.metric_code} 的当前预测影响最大。"
    else:
        summary = "当前模型没有可用于诊断的特征贡献。"
    diagnosis = DiagnosisResult(
        prediction_result_id=prediction.id,
        production_run_id=prediction.production_run_id,
        measurement_point_id=prediction.measurement_point_id,
        metric_code=prediction.metric_code,
        summary=summary,
        factor_contributions=top_factors,
        confidence=prediction.confidence,
        causality_status="CORRELATION_ONLY",
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


def recommend_with_model(
    db: Session,
    model: ModelVersion,
    production_run_id: str,
    measurement_point_id: str,
    target_min: float | None,
    target_max: float | None,
    max_actions: int,
    max_step_ratio: float,
) -> dict:
    _ensure_model_scope(model)
    production_run = db.get(ProductionRun, production_run_id)
    if not production_run:
        raise HTTPException(status_code=404, detail="生产事件不存在")
    point = db.get(MeasurementPoint, measurement_point_id)
    if not point:
        raise HTTPException(status_code=404, detail="测量点不存在")
    target_source = "USER_INPUT"
    target_standard = None
    if target_min is None and target_max is None:
        target_standard = resolve_quality_standard(
            db,
            _target_family(model.target_metric),
            model.target_metric,
            production_run,
            point,
        )
        if not target_standard or (
            target_standard.min_value is None and target_standard.max_value is None
        ):
            raise HTTPException(
                status_code=422,
                detail="当前车型、颜色和点位没有可用的生效质量标准，请先维护标准或填写期望范围",
            )
        target_min = target_standard.min_value
        target_max = target_standard.max_value
        target_source = f"QUALITY_STANDARD:{target_standard.standard_no}:{target_standard.version}"
    prediction = predict_with_model(
        db,
        model,
        production_run_id=production_run_id,
        measurement_point_id=measurement_point_id,
        persist_result=False,
    )
    current_prediction = prediction["predicted_value"]
    if target_min is not None and current_prediction < target_min:
        desired_direction = 1.0
        target_gap = target_min - current_prediction
    elif target_max is not None and current_prediction > target_max:
        desired_direction = -1.0
        target_gap = current_prediction - target_max
    else:
        raise HTTPException(status_code=409, detail="当前预测已满足目标范围，无需生成调整建议")

    snapshot = db.scalar(
        select(PointFeatureSnapshot).where(
            PointFeatureSnapshot.production_run_id == production_run_id,
            PointFeatureSnapshot.measurement_point_id == measurement_point_id,
            PointFeatureSnapshot.feature_set_version == model.feature_set_version,
            PointFeatureSnapshot.target_family == _target_family(model.target_metric),
        )
    )
    payload = model.model_payload
    candidates = []
    missing_constraint_sources: set[str] = set()
    for feature_name, scale, coefficient in zip(
        payload["feature_names"], payload["scales"], payload["coefficients"], strict=True
    ):
        parameter_code = feature_name.split(".", 1)[-1]
        process_stage = feature_name.split(".", 1)[0].upper()
        definition = db.scalar(
            select(ParameterDefinition).where(ParameterDefinition.code == parameter_code)
        )
        if (
            not definition
            or not definition.is_recommendable
            or feature_name not in snapshot.feature_values
        ):
            continue
        constraint_source = _resolve_constraint_source(
            db,
            definition,
            production_run.factory_id,
            process_stage,
            production_run.started_at or datetime.now(UTC),
        )
        if not constraint_source:
            missing_constraint_sources.add(parameter_code)
            continue
        hard_min = constraint_source.lower_limit
        hard_max = constraint_source.upper_limit
        current_value = float(snapshot.feature_values[feature_name])
        slope = coefficient / scale
        if slope == 0:
            continue
        change_direction = desired_direction if slope > 0 else -desired_direction
        available = (
            hard_max - current_value
            if change_direction > 0
            else current_value - hard_min
        )
        step = min(
            max(0.0, available),
            (hard_max - hard_min) * max_step_ratio,
        )
        if step <= 0:
            continue
        delta = step * change_direction
        expected_impact = slope * delta
        if expected_impact * desired_direction <= 0:
            continue
        candidates.append(
            {
                "feature_name": feature_name,
                "parameter_code": parameter_code,
                "parameter_name": definition.name,
                "process_stage": process_stage,
                "current_value": current_value,
                "recommended_value": current_value + delta,
                "unit": definition.unit,
                "hard_min": hard_min,
                "hard_max": hard_max,
                "constraint_source_id": constraint_source.id,
                "constraint_source_code": constraint_source.constraint_code,
                "constraint_source_version": constraint_source.version,
                "constraint_source_type": constraint_source.source_type,
                "constraint_source_uri": constraint_source.source_uri,
                "expected_impact": expected_impact,
            }
        )
    candidates.sort(key=lambda item: abs(item["expected_impact"]), reverse=True)
    selected = []
    accumulated_impact = 0.0
    for candidate in candidates:
        selected.append(candidate)
        accumulated_impact += candidate["expected_impact"]
        if len(selected) >= max_actions or abs(accumulated_impact) >= target_gap:
            break
    if not selected:
        if missing_constraint_sources:
            missing = ", ".join(sorted(missing_constraint_sources))
            raise HTTPException(status_code=422, detail=f"缺少已批准约束来源: {missing}")
        raise HTTPException(
            status_code=422,
            detail="没有满足已批准约束来源且已启用推荐的可调整参数",
        )

    metric_definition = db.scalar(
        select(QualityMetricDefinition).where(QualityMetricDefinition.code == model.target_metric)
    )
    recommendation_no = f"REC-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    recommendation = Recommendation(
        recommendation_no=recommendation_no,
        production_run_id=production_run_id,
        measurement_point_id=measurement_point_id,
        target_quality_type=metric_definition.quality_type if metric_definition else "UNKNOWN",
        target_metric=model.target_metric,
        diagnosis_summary=(
            "基于已验收模型的参数贡献度、已批准硬边界及"
            f"目标来源 {target_source} 生成受约束参数建议。"
        ),
        predicted_improvement=accumulated_impact,
        confidence=prediction["confidence"],
        status="PENDING",
        model_version=f"{model.model_code}:{model.version}",
        constraints_checked=True,
    )
    db.add(recommendation)
    db.flush()
    actions = []
    for candidate in selected:
        action = RecommendationAction(
            recommendation_id=recommendation.id,
            process_stage=candidate["process_stage"],
            parameter_code=candidate["parameter_code"],
            parameter_name=candidate["parameter_name"],
            current_value=candidate["current_value"],
            recommended_value=candidate["recommended_value"],
            unit=candidate["unit"],
            hard_min=candidate["hard_min"],
            hard_max=candidate["hard_max"],
            constraint_source_id=candidate["constraint_source_id"],
            constraint_source_code=candidate["constraint_source_code"],
            constraint_source_version=candidate["constraint_source_version"],
            constraint_source_type=candidate["constraint_source_type"],
            constraint_source_uri=candidate["constraint_source_uri"],
        )
        db.add(action)
        actions.append(action)
    db.commit()
    db.refresh(recommendation)
    return {
        "recommendation_id": recommendation.id,
        "recommendation_no": recommendation.recommendation_no,
        "status": recommendation.status,
        "metric_code": model.target_metric,
        "target_min": target_min,
        "target_max": target_max,
        "target_source": target_source,
        "current_prediction": current_prediction,
        "expected_prediction": current_prediction + accumulated_impact,
        "predicted_improvement": accumulated_impact,
        "confidence": recommendation.confidence,
        "constraints_checked": recommendation.constraints_checked,
        "actions": [
            {
                "id": action.id,
                "process_stage": action.process_stage,
                "parameter_code": action.parameter_code,
                "parameter_name": action.parameter_name,
                "current_value": action.current_value,
                "recommended_value": action.recommended_value,
                "unit": action.unit,
                "hard_min": action.hard_min,
                "hard_max": action.hard_max,
                "constraint_source_code": action.constraint_source_code,
                "constraint_source_version": action.constraint_source_version,
                "constraint_source_type": action.constraint_source_type,
                "constraint_source_uri": action.constraint_source_uri,
            }
            for action in actions
        ],
    }
