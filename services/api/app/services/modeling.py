from datetime import UTC, datetime
from math import sqrt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    DiagnosisResult,
    ModelVersion,
    ParameterDefinition,
    PointFeatureSnapshot,
    PredictionResult,
    QualityMeasurement,
    QualityMetricValue,
    QualityMetricDefinition,
    Recommendation,
    RecommendationAction,
)


def _target_value(
    db: Session, production_run_id: str, measurement_point_id: str, target_metric: str
) -> float | None:
    metric = db.scalar(
        select(QualityMetricValue)
        .join(QualityMeasurement, QualityMeasurement.id == QualityMetricValue.measurement_id)
        .where(
            QualityMeasurement.production_run_id == production_run_id,
            QualityMeasurement.measurement_point_id == measurement_point_id,
            QualityMeasurement.is_valid.is_(True),
            QualityMetricValue.metric_code == target_metric,
        )
        .order_by(QualityMeasurement.measured_at.desc())
    )
    if not metric:
        return None
    return metric.corrected_value if metric.corrected_value is not None else metric.raw_value


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

    predictions = [
        intercept + sum(coefficient * value for coefficient, value in zip(coefficients, row, strict=True))
        for row in x_rows
    ]
    errors = [prediction - target for prediction, target in zip(predictions, targets, strict=True)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = sqrt(sum(error**2 for error in errors) / len(errors))
    total_variance = sum((target - intercept) ** 2 for target in targets)
    r2 = 1 - sum(error**2 for error in errors) / total_variance if total_variance else 1.0

    return {
        "feature_names": feature_names,
        "means": means,
        "scales": scales,
        "coefficients": coefficients,
        "intercept": intercept,
        "residual_std": rmse,
        "evaluation_metrics": {
            "training_mae": round(mae, 6),
            "training_rmse": round(rmse, 6),
            "training_r2": round(r2, 6),
        },
    }


def train_model(db: Session, payload) -> ModelVersion:
    if db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_code == payload.model_code,
            ModelVersion.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="模型代码与版本已存在")

    snapshots = list(
        db.scalars(
            select(PointFeatureSnapshot).where(
                PointFeatureSnapshot.feature_set_version == payload.feature_set_version
            )
        )
    )
    samples = []
    for snapshot in snapshots:
        target = _target_value(
            db, snapshot.production_run_id, snapshot.measurement_point_id, payload.target_metric
        )
        numeric_features = {
            key: float(value)
            for key, value in snapshot.feature_values.items()
            if isinstance(value, int | float) and not isinstance(value, bool)
        }
        if target is not None and numeric_features:
            samples.append((numeric_features, target))
    if len(samples) < payload.min_samples:
        raise HTTPException(
            status_code=422,
            detail=f"有效训练样本不足：需要 {payload.min_samples}，当前 {len(samples)}",
        )

    fitted = _fit_ridge(samples, payload.ridge_lambda)
    now = datetime.now(UTC)
    model = ModelVersion(
        model_code=payload.model_code,
        version=payload.version,
        model_type="RIDGE_REGRESSION_BASELINE",
        target_metric=payload.target_metric,
        feature_set_version=payload.feature_set_version,
        artifact_uri=f"mysql://model-version/{payload.model_code}/{payload.version}",
        model_payload={
            key: value for key, value in fitted.items() if key != "evaluation_metrics"
        },
        evaluation_metrics=fitted["evaluation_metrics"],
        training_sample_count=len(samples),
        trained_at=now,
        status="ACTIVE",
    )
    db.add(model)
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
    snapshot = db.scalar(
        select(PointFeatureSnapshot).where(
            PointFeatureSnapshot.production_run_id == production_run_id,
            PointFeatureSnapshot.measurement_point_id == measurement_point_id,
            PointFeatureSnapshot.feature_set_version == model.feature_set_version,
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
    snapshot = db.scalar(
        select(PointFeatureSnapshot).where(
            PointFeatureSnapshot.production_run_id == prediction.production_run_id,
            PointFeatureSnapshot.measurement_point_id == prediction.measurement_point_id,
            PointFeatureSnapshot.feature_set_version == model.feature_set_version,
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
