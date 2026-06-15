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
    ModelAcceptanceDecision,
    ModelVersion,
    ParameterDefinition,
    PointFeatureSnapshot,
    PredictionResult,
    QualityMeasurement,
    QualityMetricValue,
    QualityMetricDefinition,
    ProductionRun,
    Recommendation,
    RecommendationAction,
)


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
    errors = [prediction - target for prediction, target in zip(predictions, targets, strict=True)]
    mean_target = sum(targets) / len(targets)
    total_variance = sum((target - mean_target) ** 2 for target in targets)
    residual_variance = sum(error**2 for error in errors)
    return {
        f"{prefix}_mae": round(sum(abs(error) for error in errors) / len(errors), 6),
        f"{prefix}_rmse": round(sqrt(residual_variance / len(errors)), 6),
        f"{prefix}_r2": round(
            1 - residual_variance / total_variance
            if total_variance
            else (1.0 if residual_variance == 0 else 0.0),
            6,
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


def _fit_ridge(samples: list[tuple[dict[str, float], float]], ridge_lambda: float) -> dict:
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

    # Coordinate descent is stable for small, correlated industrial tabular datasets.
    for _iteration in range(200):
        for feature_index in range(len(feature_names)):
            numerator = 0.0
            denominator = ridge_lambda
            for row, target in zip(x_rows, centered_targets, strict=True):
                residual_without_feature = target - sum(
                    coefficient * value
                    for index, (coefficient, value) in enumerate(
                        zip(coefficients, row, strict=True)
                    )
                    if index != feature_index
                )
                numerator += row[feature_index] * residual_without_feature
                denominator += row[feature_index] ** 2
            coefficients[feature_index] = numerator / denominator if denominator else 0.0

    fitted = {
        "feature_names": feature_names,
        "means": means,
        "scales": scales,
        "coefficients": coefficients,
        "intercept": intercept,
    }
    predictions = _predict_samples(fitted, samples)
    metrics = _regression_metrics(predictions, targets, "training")
    fitted["residual_std"] = metrics["training_rmse"]
    fitted["evaluation_metrics"] = metrics
    return fitted


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

    rows = db.execute(
        select(PointFeatureSnapshot, ProductionRun)
        .join(ProductionRun, ProductionRun.id == PointFeatureSnapshot.production_run_id)
        .where(
            PointFeatureSnapshot.feature_set_version == payload.feature_set_version,
            PointFeatureSnapshot.target_family == _target_family(payload.target_metric),
        )
        .order_by(ProductionRun.started_at, PointFeatureSnapshot.measurement_point_id)
    ).all()
    candidates = []
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
                "snapshot": snapshot,
                "run": run,
                "target": float(target_observation["value"]),
                "target_measurement_id": target_observation["measurement_id"],
                "features": features,
                "group_value": group_value,
            }
        )
    groups: dict[str, list[dict]] = {}
    for candidate in candidates:
        groups.setdefault(candidate["group_value"], []).append(candidate)
    if not candidates:
        raise HTTPException(
            status_code=422,
            detail="没有同时具备受批准数值特征和 VERIFIED 目标质量结果的样本",
        )
    ordered_groups = sorted(
        groups,
        key=lambda group: min(_time_key(item["run"].started_at) for item in groups[group]),
    )
    required_groups = payload.min_train_groups + payload.min_validation_groups
    if len(ordered_groups) < required_groups:
        raise HTTPException(
            status_code=422,
            detail=(
                f"独立生产分组不足：训练至少 {payload.min_train_groups} 组、"
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
    train_snapshot_ids = {item["snapshot"].id for item in train_rows}
    validation_snapshot_ids = {item["snapshot"].id for item in validation_rows}
    leakage_check = {
        "group_overlap_count": len(train_groups & validation_groups),
        "snapshot_overlap_count": len(train_snapshot_ids & validation_snapshot_ids),
        "temporal_order_valid": max(_time_key(item["run"].started_at) for item in train_rows)
        <= min(_time_key(item["run"].started_at) for item in validation_rows),
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
        group_key="BODY_OR_RUN",
        holdout_ratio=payload.holdout_ratio,
        status="BUILT",
        sample_count=len(candidates),
        group_count=len(groups),
        train_sample_count=len(train_rows),
        validation_sample_count=len(validation_rows),
        train_group_count=len(train_groups),
        validation_group_count=len(validation_groups),
        cutoff_at=min(validation_rows, key=lambda item: _time_key(item["run"].started_at))[
            "run"
        ].started_at,
        feature_names=feature_names,
        lineage={
            "point_feature_snapshot_ids": [item["snapshot"].id for item in candidates],
            "production_run_ids": sorted({item["run"].id for item in candidates}),
            "target_measurement_ids": [
                item["target_measurement_id"] for item in candidates
            ],
            "target_reliability_status": "VERIFIED",
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
                point_feature_snapshot_id=item["snapshot"].id,
                production_run_id=item["run"].id,
                measurement_point_id=item["snapshot"].measurement_point_id,
                target_measurement_id=item["target_measurement_id"],
                group_value=item["group_value"],
                split="VALIDATION" if item["group_value"] in validation_groups else "TRAIN",
                target_value=item["target"],
                feature_values={name: item["features"][name] for name in feature_names},
                occurred_at=item["run"].started_at,
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
    train_samples = [
        (member.feature_values, member.target_value)
        for member in members
        if member.split == "TRAIN"
    ]
    validation_samples = [
        (member.feature_values, member.target_value)
        for member in members
        if member.split == "VALIDATION"
    ]
    if len(train_samples) < payload.min_samples:
        raise HTTPException(
            status_code=422,
            detail=f"有效训练样本不足：需要 {payload.min_samples}，当前 {len(train_samples)}",
        )
    if not validation_samples:
        raise HTTPException(status_code=422, detail="数据集没有独立验证样本")

    fitted = _fit_ridge(train_samples, payload.ridge_lambda)
    try:
        require_scope_safe_model(
            payload.target_metric,
            payload.feature_set_version,
            fitted["feature_names"],
        )
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    validation_predictions = _predict_samples(fitted, validation_samples)
    evaluation_metrics = {
        **fitted["evaluation_metrics"],
        **_regression_metrics(
            validation_predictions,
            [target for _features, target in validation_samples],
            "validation",
        ),
        "train_group_count": dataset.train_group_count,
        "validation_group_count": dataset.validation_group_count,
        "leakage_check_passed": dataset.leakage_check.get("passed", False),
    }
    now = datetime.now(UTC)
    model = ModelVersion(
        model_code=payload.model_code,
        version=payload.version,
        model_type="RIDGE_REGRESSION_BASELINE",
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
    db.commit()
    db.refresh(model)
    return model


def record_model_acceptance(db: Session, model: ModelVersion, payload) -> ModelAcceptanceDecision:
    if not model.dataset_snapshot_id:
        raise HTTPException(status_code=409, detail="旧模型没有受治理的数据集快照，不能验收")
    dataset = db.get(DatasetSnapshot, model.dataset_snapshot_id)
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
        **threshold_checks,
    }
    checks["all_required_checks_passed"] = all(checks.values())
    if payload.decision == "ACCEPTED" and not checks["all_required_checks_passed"]:
        raise HTTPException(status_code=422, detail="模型未满足验收检查，不能记录为通过")
    decision = ModelAcceptanceDecision(
        model_version_id=model.id,
        dataset_snapshot_id=model.dataset_snapshot_id,
        decision=payload.decision,
        criteria={
            "max_validation_rmse": payload.max_validation_rmse,
            "min_validation_r2": payload.min_validation_r2,
        },
        checks=checks,
        decided_by=payload.decided_by,
        decided_at=datetime.now(UTC),
        comment=payload.comment,
    )
    if payload.decision == "REJECTED" and model.status == "ACTIVE":
        model.status = "RETIRED"
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
        for active_model in db.scalars(
            select(ModelVersion).where(
                ModelVersion.model_code == model.model_code,
                ModelVersion.target_metric == model.target_metric,
                ModelVersion.status == "ACTIVE",
                ModelVersion.id != model.id,
            )
        ):
            active_model.status = "RETIRED"
    model.status = next_status
    db.commit()
    db.refresh(model)
    return model


def predict_with_model(
    db: Session,
    model: ModelVersion,
    production_run_id: str,
    measurement_point_id: str,
    persist_result: bool = True,
) -> dict:
    _ensure_model_scope(model)
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
    confidence = round(min(0.99, 0.5 + 0.49 * feature_completeness), 4)
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
        "predicted_value": predicted_value,
        "lower_bound": predicted_value - 1.96 * residual_std,
        "upper_bound": predicted_value + 1.96 * residual_std,
        "confidence": confidence,
        "feature_completeness": feature_completeness,
    }


def diagnose_prediction(db: Session, prediction: PredictionResult) -> DiagnosisResult:
    model = db.get(ModelVersion, prediction.model_version_id)
    _ensure_model_scope(model)
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
    if target_min is None and target_max is None:
        raise HTTPException(status_code=422, detail="必须提供目标下限或目标上限")
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
    for feature_name, scale, coefficient in zip(
        payload["feature_names"], payload["scales"], payload["coefficients"], strict=True
    ):
        parameter_code = feature_name.split(".", 1)[-1]
        definition = db.scalar(
            select(ParameterDefinition).where(ParameterDefinition.code == parameter_code)
        )
        if (
            not definition
            or not definition.is_recommendable
            or definition.hard_min is None
            or definition.hard_max is None
            or feature_name not in snapshot.feature_values
        ):
            continue
        current_value = float(snapshot.feature_values[feature_name])
        slope = coefficient / scale
        if slope == 0:
            continue
        change_direction = desired_direction if slope > 0 else -desired_direction
        available = (
            definition.hard_max - current_value
            if change_direction > 0
            else current_value - definition.hard_min
        )
        step = min(
            max(0.0, available),
            (definition.hard_max - definition.hard_min) * max_step_ratio,
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
                "process_stage": feature_name.split(".", 1)[0].upper(),
                "current_value": current_value,
                "recommended_value": current_value + delta,
                "unit": definition.unit,
                "hard_min": definition.hard_min,
                "hard_max": definition.hard_max,
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
        raise HTTPException(
            status_code=422,
            detail="没有满足硬边界且已启用推荐的可调整参数",
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
        diagnosis_summary="基于线性基础模型贡献度和已配置硬边界生成受约束参数建议。",
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
            }
            for action in actions
        ],
    }
