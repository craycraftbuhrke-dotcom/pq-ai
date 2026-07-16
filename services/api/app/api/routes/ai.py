from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.referential_integrity import check_fk
from app.db.session import get_db
from app.domain.scope_policy import ScopeViolation, require_approved_target_metric
from app.models.domain import (
    ClosedLoopEvaluation,
    ControlledTrial,
    DiagnosisResult,
    MeasurementPoint,
    ModelVersion,
    PredictionResult,
    ProgramRollbackExecution,
    QualityIssueTask,
    QualityMeasurement,
    QualityMetricValue,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
    SprayProgramVersion,
    VersionStatus,
)
from app.schemas.common import (
    ControlledTrialApproval,
    ControlledTrialCreate,
    DiagnosisRequest,
    PredictionRequest,
    RecommendationApproval,
    RecommendationExecution,
    RecommendationRequest,
    RecommendationVerification,
    RollbackExecutionCreate,
)
from app.schemas.process import AiOverviewSummary

router = APIRouter(prefix="/ai", tags=["ai-closed-loop"])


def _validate_target_metrics(metric_codes: list[str]) -> None:
    try:
        for metric_code in metric_codes:
            require_approved_target_metric(metric_code)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
                "constraint_source_code": action.constraint_source_code,
                "constraint_source_version": action.constraint_source_version,
                "constraint_source_type": action.constraint_source_type,
                "constraint_source_uri": action.constraint_source_uri,
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


def _serialize_controlled_trial(trial: ControlledTrial) -> dict:
    return {
        "id": trial.id,
        "trial_no": trial.trial_no,
        "recommendation_id": trial.recommendation_id,
        "production_run_id": trial.production_run_id,
        "measurement_point_id": trial.measurement_point_id,
        "target_metric": trial.target_metric,
        "hypothesis": trial.hypothesis,
        "evidence_type": trial.evidence_type,
        "expected_outcome": trial.expected_outcome,
        "risk_assessment": trial.risk_assessment,
        "rollback_plan": trial.rollback_plan,
        "sustained_observation_plan": trial.sustained_observation_plan,
        "constraint_evidence": trial.constraint_evidence,
        "status": trial.status,
        "requested_by": trial.requested_by,
        "requested_at": trial.requested_at,
        "approved_by": trial.approved_by,
        "approved_at": trial.approved_at,
        "approval_comment": trial.approval_comment,
        "started_at": trial.started_at,
        "completed_at": trial.completed_at,
        "completion_summary": trial.completion_summary,
        "created_at": trial.created_at,
        "updated_at": trial.updated_at,
    }


def _serialize_rollback_execution(rollback: ProgramRollbackExecution) -> dict:
    return {
        "id": rollback.id,
        "rollback_no": rollback.rollback_no,
        "recommendation_id": rollback.recommendation_id,
        "controlled_trial_id": rollback.controlled_trial_id,
        "rollback_to_program_version_id": rollback.rollback_to_program_version_id,
        "rollback_reason": rollback.rollback_reason,
        "execution_note": rollback.execution_note,
        "executed_by": rollback.executed_by,
        "executed_at": rollback.executed_at,
        "status": rollback.status,
        "action_snapshot": rollback.action_snapshot,
        "verified_by": rollback.verified_by,
        "verified_at": rollback.verified_at,
        "verification_comment": rollback.verification_comment,
        "created_at": rollback.created_at,
        "updated_at": rollback.updated_at,
    }


@router.post("/predictions")
def predict(payload: PredictionRequest) -> dict:
    _validate_target_metrics(payload.target_metrics)
    raise HTTPException(
        status_code=410,
        detail="旧版预测接口已禁用；请使用 /ai/models/{model_version_id}/predict 受治理模型接口",
    )


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
            "applicability_status": prediction.applicability_status,
            "ood_status": prediction.ood_status,
            "governance_evidence": prediction.governance_evidence,
            "predicted_at": prediction.predicted_at,
        }
        for prediction in predictions
    ]


@router.post("/diagnoses")
def diagnose(payload: DiagnosisRequest) -> dict:
    _validate_target_metrics([payload.observed_metric])
    raise HTTPException(
        status_code=410,
        detail="旧版诊断接口已禁用；请使用受治理模型产生的预测结果诊断接口",
    )


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
    _validate_target_metrics([payload.target_metric])
    raise HTTPException(
        status_code=410,
        detail="旧版推荐接口已禁用；请使用 /ai/models/{model_version_id}/recommend 受治理推荐接口",
    )


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


@router.get("/controlled-trials")
def list_controlled_trials(db: Session = Depends(get_db)) -> list[dict]:
    trials = list(
        db.scalars(select(ControlledTrial).order_by(ControlledTrial.created_at.desc()).limit(200))
    )
    return [_serialize_controlled_trial(trial) for trial in trials]


@router.get("/controlled-trials/{trial_id}")
def get_controlled_trial(trial_id: str, db: Session = Depends(get_db)) -> dict:
    trial = db.get(ControlledTrial, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="受控试验不存在")
    return _serialize_controlled_trial(trial)


@router.post("/recommendations/{recommendation_id}/controlled-trial")
def create_controlled_trial(
    recommendation_id: str,
    payload: ControlledTrialCreate,
    db: Session = Depends(get_db),
) -> dict:
    recommendation = db.get(Recommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="推荐任务不存在")
    if recommendation.status != "PENDING":
        raise HTTPException(status_code=409, detail="仅待审批推荐可以创建受控试验计划")
    if not recommendation.constraints_checked:
        raise HTTPException(status_code=422, detail="推荐尚未通过约束校验，不能创建试验计划")
    existing = db.scalar(
        select(ControlledTrial).where(ControlledTrial.recommendation_id == recommendation.id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="该推荐已存在受控试验计划")
    actions = list(
        db.scalars(
            select(RecommendationAction).where(
                RecommendationAction.recommendation_id == recommendation.id
            )
        )
    )
    now = datetime.now(UTC)
    trial = ControlledTrial(
        recommendation_id=recommendation.id,
        trial_no=f"TRIAL-{now.strftime('%Y%m%d%H%M%S%f')}",
        production_run_id=recommendation.production_run_id,
        measurement_point_id=recommendation.measurement_point_id,
        target_metric=recommendation.target_metric,
        hypothesis=payload.hypothesis,
        evidence_type=payload.evidence_type,
        expected_outcome=payload.expected_outcome,
        risk_assessment=payload.risk_assessment,
        rollback_plan=payload.rollback_plan,
        sustained_observation_plan=payload.sustained_observation_plan,
        constraint_evidence={
            "constraints_checked": recommendation.constraints_checked,
            "model_version": recommendation.model_version,
            "predicted_improvement": recommendation.predicted_improvement,
            "actions": [
                {
                    "action_id": action.id,
                    "parameter_code": action.parameter_code,
                    "current_value": action.current_value,
                    "recommended_value": action.recommended_value,
                    "hard_min": action.hard_min,
                    "hard_max": action.hard_max,
                    "unit": action.unit,
                    "constraint_source_code": action.constraint_source_code,
                    "constraint_source_version": action.constraint_source_version,
                    "constraint_source_type": action.constraint_source_type,
                    "constraint_source_uri": action.constraint_source_uri,
                }
                for action in actions
            ],
        },
        status="PLANNED",
        requested_by=payload.requested_by,
        requested_at=now,
    )
    db.add(trial)
    db.commit()
    db.refresh(trial)
    return _serialize_controlled_trial(trial)


@router.post("/controlled-trials/{trial_id}/approval")
def approve_controlled_trial(
    trial_id: str,
    payload: ControlledTrialApproval,
    db: Session = Depends(get_db),
) -> dict:
    trial = db.get(ControlledTrial, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="受控试验不存在")
    if trial.status != "PLANNED":
        raise HTTPException(status_code=409, detail="仅已计划试验可以审批")
    trial.status = "APPROVED" if payload.approved else "REJECTED"
    trial.approved_by = payload.approved_by
    trial.approved_at = datetime.now(UTC)
    trial.approval_comment = payload.comment
    db.commit()
    db.refresh(trial)
    return _serialize_controlled_trial(trial)


@router.get("/rollback-executions")
def list_rollback_executions(db: Session = Depends(get_db)) -> list[dict]:
    rollbacks = list(
        db.scalars(
            select(ProgramRollbackExecution)
            .order_by(ProgramRollbackExecution.executed_at.desc())
            .limit(200)
        )
    )
    return [_serialize_rollback_execution(rollback) for rollback in rollbacks]


@router.post("/controlled-trials/{trial_id}/rollback")
def record_trial_rollback(
    trial_id: str,
    payload: RollbackExecutionCreate,
    db: Session = Depends(get_db),
) -> dict:
    trial = db.get(ControlledTrial, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="受控试验不存在")
    if trial.status != "INEFFECTIVE":
        raise HTTPException(status_code=409, detail="仅未达预期的受控试验可以记录回滚")
    if db.scalar(
        select(ProgramRollbackExecution).where(
            ProgramRollbackExecution.controlled_trial_id == trial.id
        )
    ):
        raise HTTPException(status_code=409, detail="该受控试验已记录回滚执行")
    if payload.rollback_to_program_version_id and not db.get(
        SprayProgramVersion, payload.rollback_to_program_version_id
    ):
        raise HTTPException(status_code=404, detail="回滚目标程序版本不存在")
    actions = list(
        db.scalars(
            select(RecommendationAction).where(
                RecommendationAction.recommendation_id == trial.recommendation_id
            )
        )
    )
    now = datetime.now(UTC)
    rollback = ProgramRollbackExecution(
        rollback_no=f"RBK-{now.strftime('%Y%m%d%H%M%S%f')}",
        recommendation_id=trial.recommendation_id,
        controlled_trial_id=trial.id,
        rollback_to_program_version_id=payload.rollback_to_program_version_id,
        rollback_reason=payload.rollback_reason,
        execution_note=payload.execution_note,
        executed_by=payload.executed_by,
        executed_at=now,
        status="EXECUTED",
        action_snapshot={
            "recommendation_id": trial.recommendation_id,
            "trial_no": trial.trial_no,
            "actions": [
                {
                    "action_id": action.id,
                    "process_stage": action.process_stage,
                    "parameter_code": action.parameter_code,
                    "parameter_name": action.parameter_name,
                    "current_value": action.current_value,
                    "recommended_value": action.recommended_value,
                    "executed_value": action.executed_value,
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
        },
    )
    trial.status = "ROLLED_BACK"
    trial.completed_at = now
    trial.completion_summary = "受控试验未达预期，已记录程序/参数回滚执行。"
    db.add(rollback)
    db.commit()
    db.refresh(rollback)
    return _serialize_rollback_execution(rollback)


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
    check_fk(db, Recommendation, recommendation_id, label="推荐任务")
    recommendation = db.get(Recommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="推荐任务不存在")
    if recommendation.status != "PENDING":
        raise HTTPException(status_code=409, detail="仅待审批推荐可以执行审批")
    if payload.approved and not recommendation.constraints_checked:
        raise HTTPException(status_code=422, detail="推荐尚未通过安全约束校验")
    trial = db.scalar(
        select(ControlledTrial).where(ControlledTrial.recommendation_id == recommendation.id)
    )
    if payload.approved and (not trial or trial.status != "APPROVED"):
        raise HTTPException(status_code=422, detail="推荐必须先具备已批准的受控试验计划")
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
                "constraint_source_code": action.constraint_source_code,
                "constraint_source_version": action.constraint_source_version,
                "constraint_source_type": action.constraint_source_type,
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
    check_fk(db, Recommendation, recommendation_id, label="推荐任务")
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
    trial = db.scalar(
        select(ControlledTrial).where(ControlledTrial.recommendation_id == recommendation.id)
    )
    if trial and trial.status == "APPROVED":
        trial.status = "RUNNING"
        trial.started_at = recommendation.executed_at
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
    check_fk(db, Recommendation, recommendation_id, label="推荐任务")
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
        not verified_measurement.is_valid
        or verified_measurement.reliability_status != "VERIFIED"
    ):
        raise HTTPException(status_code=422, detail="复测记录未通过仪器与测量可靠性门禁")
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
            QualityMeasurement.is_valid.is_(True),
            QualityMeasurement.reliability_status == "VERIFIED",
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
    trial = db.scalar(
        select(ControlledTrial).where(ControlledTrial.recommendation_id == recommendation.id)
    )
    if trial and trial.status in {"APPROVED", "RUNNING"}:
        trial.status = "VERIFIED" if evaluation.is_effective else "INEFFECTIVE"
        trial.completed_at = datetime.now(UTC)
        trial.completion_summary = (
            "受控试验复测有效，推荐可进入持续观察。"
            if evaluation.is_effective
            else "受控试验复测未达预期，需执行回滚或重新制定假设。"
        )
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


@router.get("/overview-summary", response_model=AiOverviewSummary)
def ai_overview_summary(db: Session = Depends(get_db)) -> AiOverviewSummary:
    models_total = int(db.scalar(select(func.count()).select_from(ModelVersion)) or 0)
    models_approved = int(
        db.scalar(
            select(func.count())
            .select_from(ModelVersion)
            .where(ModelVersion.status == VersionStatus.APPROVED)
        )
        or 0
    )
    latest_model = db.scalar(
        select(ModelVersion)
        .where(ModelVersion.status == VersionStatus.APPROVED)
        .order_by(ModelVersion.trained_at.desc().nullslast())
    )

    now = datetime.now(UTC)
    predictions_24h = int(
        db.scalar(
            select(func.count())
            .select_from(PredictionResult)
            .where(PredictionResult.predicted_at >= now - timedelta(hours=24))
        )
        or 0
    )
    top_risk_prediction = db.scalar(
        select(PredictionResult)
        .where(PredictionResult.predicted_at >= now - timedelta(hours=24))
        .order_by(PredictionResult.predicted_at.desc())
    )
    top_risk_point = None
    if top_risk_prediction:
        point = db.get(MeasurementPoint, top_risk_prediction.measurement_point_id)
        top_risk_point = point.code if point else top_risk_prediction.measurement_point_id

    recommendations_total = int(
        db.scalar(select(func.count()).select_from(Recommendation)) or 0
    )
    recommendations_pending = int(
        db.scalar(
            select(func.count())
            .select_from(Recommendation)
            .where(Recommendation.status == RecommendationStatus.PENDING)
        )
        or 0
    )

    trials_total = int(db.scalar(select(func.count()).select_from(ControlledTrial)) or 0)
    trials_active = int(
        db.scalar(
            select(func.count())
            .select_from(ControlledTrial)
            .where(ControlledTrial.status.notin_(["COMPLETED", "VERIFIED", "ROLLED_BACK"]))
        )
        or 0
    )
    trials_completed = int(
        db.scalar(
            select(func.count())
            .select_from(ControlledTrial)
            .where(ControlledTrial.status.in_(["COMPLETED", "VERIFIED"]))
        )
        or 0
    )

    open_changes = int(
        db.scalar(
            select(func.count())
            .select_from(QualityIssueTask)
            .where(QualityIssueTask.status.notin_(["VERIFIED", "CLOSED"]))
        )
        or 0
    )

    return AiOverviewSummary(
        models_approved=models_approved,
        models_total=models_total,
        latest_model_metric=latest_model.target_metric if latest_model else None,
        predictions_24h=predictions_24h,
        top_risk_point=top_risk_point,
        recommendations_pending=recommendations_pending,
        recommendations_total=recommendations_total,
        trials_active=trials_active,
        trials_completed=trials_completed,
        open_changes=open_changes,
    )
