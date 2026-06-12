from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import (
    ClosedLoopEvaluation,
    DiagnosisResult,
    ModelVersion,
    PredictionResult,
    QualityMeasurement,
    QualityMetricValue,
    Recommendation,
    RecommendationAction,
)
from app.schemas.common import (
    DiagnosisRequest,
    PredictionRequest,
    RecommendationApproval,
    RecommendationExecution,
    RecommendationRequest,
    RecommendationVerification,
)
from app.services.demo import demo_recommendation, prediction_result

router = APIRouter(prefix="/ai", tags=["ai-closed-loop"])


def _utc_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _serialize_recommendation(recommendation: Recommendation, db: Session) -> dict:
    evaluation = db.scalar(
        select(ClosedLoopEvaluation).where(
            ClosedLoopEvaluation.recommendation_id == recommendation.id
        )
    )
    actions = list(
        db.scalars(
            select(RecommendationAction)
            .where(RecommendationAction.recommendation_id == recommendation.id)
            .order_by(RecommendationAction.created_at)
        )
    )
    return {
        "id": recommendation.id,
        "recommendation_no": recommendation.recommendation_no,
        "production_run_id": recommendation.production_run_id,
        "measurement_point_id": recommendation.measurement_point_id,
        "target_quality_type": recommendation.target_quality_type,
        "target_metric": recommendation.target_metric,
        "diagnosis_summary": recommendation.diagnosis_summary,
        "predicted_improvement": recommendation.predicted_improvement,
        "confidence": recommendation.confidence,
        "status": recommendation.status,
        "model_version": recommendation.model_version,
        "constraints_checked": recommendation.constraints_checked,
        "approved_by": recommendation.approved_by,
        "approved_at": recommendation.approved_at,
        "executed_by": recommendation.executed_by,
        "executed_at": recommendation.executed_at,
        "created_at": recommendation.created_at,
        "actions": [
            {
                "id": action.id,
                "process_stage": action.process_stage,
                "brush_no": action.brush_no,
                "parameter_code": action.parameter_code,
                "parameter_name": action.parameter_name,
                "current_value": action.current_value,
                "recommended_value": action.recommended_value,
                "executed_value": action.executed_value,
                "unit": action.unit,
                "hard_min": action.hard_min,
                "hard_max": action.hard_max,
            }
            for action in actions
        ],
        "evaluation": (
            {
                "id": evaluation.id,
                "baseline_value": evaluation.baseline_value,
                "verified_value": evaluation.verified_value,
                "actual_improvement": evaluation.actual_improvement,
                "is_effective": evaluation.is_effective,
                "verified_at": evaluation.verified_at,
                "verified_by": evaluation.verified_by,
                "conclusion": evaluation.conclusion,
            }
            if evaluation
            else None
        ),
    }


@router.post("/predictions")
def predict(payload: PredictionRequest) -> dict:
    return prediction_result(payload.model_dump())


@router.get("/predictions")
def list_predictions(db: Session = Depends(get_db)) -> list[dict]:
    predictions = list(
        db.scalars(select(PredictionResult).order_by(PredictionResult.predicted_at.desc()).limit(200))
    )
    models = {
        model.id: model
        for model in db.scalars(
            select(ModelVersion).where(
                ModelVersion.id.in_({prediction.model_version_id for prediction in predictions})
            )
        )
    }
    return [
        {
            "id": prediction.id,
            "model_version_id": prediction.model_version_id,
            "model_name": (
                f"{models[prediction.model_version_id].model_code}:"
                f"{models[prediction.model_version_id].version}"
                if prediction.model_version_id in models
                else prediction.model_version_id
            ),
            "production_run_id": prediction.production_run_id,
            "measurement_point_id": prediction.measurement_point_id,
            "metric_code": prediction.metric_code,
            "predicted_value": prediction.predicted_value,
            "lower_bound": prediction.lower_bound,
            "upper_bound": prediction.upper_bound,
            "confidence": prediction.confidence,
            "predicted_at": prediction.predicted_at,
        }
        for prediction in predictions
    ]


@router.post("/diagnoses")
def diagnose(payload: DiagnosisRequest) -> dict:
    return {
        "production_run_no": payload.production_run_no,
        "measurement_point_code": payload.measurement_point_code,
        "metric": payload.observed_metric,
        "observed_value": payload.observed_value,
        "confidence": 0.87,
        "summary": "清漆二站外成型空气和材料粘度是本次质量风险的主要相关因素。",
        "factors": [
            {"parameter": "clearcoat_2_outer_air", "impact": 0.34, "direction": "negative"},
            {"parameter": "clearcoat_viscosity", "impact": 0.26, "direction": "negative"},
        ],
        "is_demo_model": True,
    }


@router.get("/diagnoses")
def list_diagnoses(db: Session = Depends(get_db)) -> list[dict]:
    diagnoses = list(
        db.scalars(select(DiagnosisResult).order_by(DiagnosisResult.created_at.desc()).limit(200))
    )
    return [
        {
            "id": diagnosis.id,
            "prediction_result_id": diagnosis.prediction_result_id,
            "production_run_id": diagnosis.production_run_id,
            "measurement_point_id": diagnosis.measurement_point_id,
            "metric_code": diagnosis.metric_code,
            "summary": diagnosis.summary,
            "factor_contributions": diagnosis.factor_contributions,
            "confidence": diagnosis.confidence,
            "causality_status": diagnosis.causality_status,
            "created_at": diagnosis.created_at,
        }
        for diagnosis in diagnoses
    ]


@router.post("/recommendations")
def recommend(payload: RecommendationRequest) -> dict:
    result = demo_recommendation()
    result["production_run_no"] = payload.production_run_no
    result["point_code"] = payload.measurement_point_code
    result["target_metric"] = payload.target_metric
    return result


@router.get("/recommendations")
def list_recommendations(db: Session = Depends(get_db)) -> list[dict]:
    recommendations = list(
        db.scalars(select(Recommendation).order_by(Recommendation.created_at.desc()).limit(100))
    )
    return [_serialize_recommendation(recommendation, db) for recommendation in recommendations]


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: str, db: Session = Depends(get_db)) -> dict:
    recommendation = db.get(Recommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="推荐任务不存在")
    return _serialize_recommendation(recommendation, db)


@router.get("/evaluations")
def list_evaluations(db: Session = Depends(get_db)) -> list[dict]:
    evaluations = list(
        db.scalars(
            select(ClosedLoopEvaluation).order_by(ClosedLoopEvaluation.verified_at.desc()).limit(200)
        )
    )
    return [
        {
            "id": evaluation.id,
            "recommendation_id": evaluation.recommendation_id,
            "baseline_value": evaluation.baseline_value,
            "verified_value": evaluation.verified_value,
            "actual_improvement": evaluation.actual_improvement,
            "is_effective": evaluation.is_effective,
            "verified_at": evaluation.verified_at,
            "verified_by": evaluation.verified_by,
            "conclusion": evaluation.conclusion,
        }
        for evaluation in evaluations
    ]


@router.post("/recommendations/{recommendation_id}/approval")
def approve_recommendation(
    recommendation_id: str,
    payload: RecommendationApproval,
    db: Session = Depends(get_db),
) -> dict:
    if recommendation_id == "rec-20260609-003":
        result = demo_recommendation()
        result["status"] = "APPROVED" if payload.approved else "REJECTED"
        result["approved_by"] = payload.approved_by
        result["approval_comment"] = payload.comment
        return result

    recommendation = db.get(Recommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="推荐任务不存在")
    if recommendation.status != "PENDING":
        raise HTTPException(status_code=409, detail="仅待审批推荐可以执行审批")
    if payload.approved and not recommendation.constraints_checked:
        raise HTTPException(status_code=422, detail="推荐尚未通过安全约束校验")
    recommendation.status = "APPROVED" if payload.approved else "REJECTED"
    recommendation.approved_by = payload.approved_by
    recommendation.approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(recommendation)
    actions = list(
        db.scalars(
            select(RecommendationAction).where(
                RecommendationAction.recommendation_id == recommendation.id
            )
        )
    )
    return {
        "id": recommendation.id,
        "recommendation_no": recommendation.recommendation_no,
        "status": recommendation.status,
        "approved_by": recommendation.approved_by,
        "approval_comment": payload.comment,
        "constraints_checked": recommendation.constraints_checked,
        "actions": [
            {
                "parameter_code": action.parameter_code,
                "current_value": action.current_value,
                "recommended_value": action.recommended_value,
                "unit": action.unit,
            }
            for action in actions
        ],
    }


@router.post("/recommendations/{recommendation_id}/execution")
def execute_recommendation(
    recommendation_id: str,
    payload: RecommendationExecution,
    db: Session = Depends(get_db),
) -> dict:
    recommendation = db.get(Recommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="推荐任务不存在")
    if recommendation.status != "APPROVED":
        raise HTTPException(status_code=409, detail="仅已批准推荐可以执行")
    actions = {
        action.id: action
        for action in db.scalars(
            select(RecommendationAction).where(
                RecommendationAction.recommendation_id == recommendation.id
            )
        )
    }
    submitted_action_ids = {execution.action_id for execution in payload.actions}
    if submitted_action_ids != set(actions):
        raise HTTPException(status_code=422, detail="必须提交全部推荐动作的实际执行值")
    for execution in payload.actions:
        action = actions.get(execution.action_id)
        if not action:
            raise HTTPException(status_code=404, detail="推荐动作不存在")
        if action.hard_min is not None and execution.executed_value < action.hard_min:
            raise HTTPException(status_code=422, detail=f"{action.parameter_name}执行值低于硬下限")
        if action.hard_max is not None and execution.executed_value > action.hard_max:
            raise HTTPException(status_code=422, detail=f"{action.parameter_name}执行值高于硬上限")
        action.executed_value = execution.executed_value
    recommendation.status = "EXECUTED"
    recommendation.executed_by = payload.executed_by
    recommendation.executed_at = datetime.now(UTC)
    db.commit()
    return {
        "id": recommendation.id,
        "status": recommendation.status,
        "executed_by": recommendation.executed_by,
        "executed_at": recommendation.executed_at,
        "actions": [
            {
                "id": action.id,
                "parameter_code": action.parameter_code,
                "recommended_value": action.recommended_value,
                "executed_value": action.executed_value,
                "unit": action.unit,
            }
            for action in actions.values()
        ],
    }


@router.post("/recommendations/{recommendation_id}/verification")
def verify_recommendation(
    recommendation_id: str,
    payload: RecommendationVerification,
    db: Session = Depends(get_db),
) -> dict:
    recommendation = db.get(Recommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="推荐任务不存在")
    if recommendation.status != "EXECUTED":
        raise HTTPException(status_code=409, detail="仅已执行推荐可以进行复测评价")
    if db.scalar(
        select(ClosedLoopEvaluation).where(
            ClosedLoopEvaluation.recommendation_id == recommendation.id
        )
    ):
        raise HTTPException(status_code=409, detail="推荐任务已完成复测评价")
    verified_measurement = db.get(QualityMeasurement, payload.verified_measurement_id)
    if (
        not verified_measurement
        or verified_measurement.production_run_id != recommendation.production_run_id
        or verified_measurement.measurement_point_id != recommendation.measurement_point_id
    ):
        raise HTTPException(status_code=422, detail="复测记录与推荐任务的生产事件或测量点不匹配")
    if (
        recommendation.executed_at
        and _utc_datetime(verified_measurement.measured_at)
        <= _utc_datetime(recommendation.executed_at)
    ):
        raise HTTPException(status_code=422, detail="复测记录必须晚于推荐任务执行时间")
    verified_metric = db.scalar(
        select(QualityMetricValue).where(
            QualityMetricValue.measurement_id == verified_measurement.id,
            QualityMetricValue.metric_code == recommendation.target_metric,
        )
    )
    if not verified_metric:
        raise HTTPException(status_code=422, detail="复测记录缺少推荐目标指标")
    baseline_metric = db.scalar(
        select(QualityMetricValue)
        .join(QualityMeasurement, QualityMeasurement.id == QualityMetricValue.measurement_id)
        .where(
            QualityMeasurement.production_run_id == recommendation.production_run_id,
            QualityMeasurement.measurement_point_id == recommendation.measurement_point_id,
            QualityMeasurement.measured_at < verified_measurement.measured_at,
            QualityMetricValue.metric_code == recommendation.target_metric,
        )
        .order_by(QualityMeasurement.measured_at.desc())
    )
    if not baseline_metric:
        raise HTTPException(status_code=422, detail="未找到复测之前的基准质量值")
    baseline_value = (
        baseline_metric.corrected_value
        if baseline_metric.corrected_value is not None
        else baseline_metric.raw_value
    )
    verified_value = (
        verified_metric.corrected_value
        if verified_metric.corrected_value is not None
        else verified_metric.raw_value
    )
    actual_improvement = verified_value - baseline_value
    evaluation = ClosedLoopEvaluation(
        recommendation_id=recommendation.id,
        baseline_value=baseline_value,
        verified_value=verified_value,
        actual_improvement=actual_improvement,
        is_effective=actual_improvement * recommendation.predicted_improvement > 0,
        verified_at=verified_measurement.measured_at,
        verified_by=payload.verified_by,
        conclusion=payload.conclusion,
    )
    db.add(evaluation)
    recommendation.status = "VERIFIED"
    db.commit()
    db.refresh(evaluation)
    return {
        "id": evaluation.id,
        "recommendation_id": recommendation.id,
        "status": recommendation.status,
        "baseline_value": evaluation.baseline_value,
        "verified_value": evaluation.verified_value,
        "actual_improvement": evaluation.actual_improvement,
        "is_effective": evaluation.is_effective,
        "verified_at": evaluation.verified_at,
        "verified_by": evaluation.verified_by,
        "conclusion": evaluation.conclusion,
    }
