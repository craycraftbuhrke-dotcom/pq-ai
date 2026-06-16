from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.scope_policy import CURRENT_FEATURE_SET_VERSION
from app.models.domain import (
    DatasetSnapshot,
    DatasetSplitMember,
    Color,
    Factory,
    MeasurementPoint,
    ModelArtifact,
    ModelAcceptancePolicy,
    ModelApplicabilityScope,
    ModelAcceptanceDecision,
    ModelOodPolicy,
    ModelValidationFold,
    ModelVersion,
    PointFeatureSnapshot,
    PredictionResult,
    ProductionRun,
    VehicleModel,
)
from app.schemas.modeling import (
    DatasetBuildRequest,
    DatasetSnapshotRead,
    DatasetSplitMemberRead,
    ModelAcceptanceDecisionRead,
    ModelAcceptanceRequest,
    ModelArtifactRead,
    ModelAcceptancePolicyCreate,
    ModelAcceptancePolicyRead,
    ModelAcceptancePolicyStatusUpdate,
    ModelApplicabilityScopeCreate,
    ModelApplicabilityScopeRead,
    ModelApplicabilityScopeStatusUpdate,
    ModelDiagnosisResponse,
    ModelDriftReport,
    ModelGovernanceCheckRequest,
    ModelGovernanceCheckResponse,
    ModelOodPolicyRead,
    ModelOodPolicyUpdate,
    ModelPredictionRequest,
    ModelPredictionResponse,
    ModelRecommendationRequest,
    ModelRecommendationResponse,
    ModelStatusUpdate,
    ModelTrainingRequest,
    ModelValidationFoldRead,
    ModelVersionRead,
)
from app.services.modeling import (
    build_dataset_snapshot,
    create_model_acceptance_policy,
    create_model_applicability_scope,
    diagnose_prediction,
    model_governance_check,
    model_drift_report,
    predict_with_model,
    recommend_with_model,
    record_model_acceptance,
    train_model,
    update_model_applicability_scope,
    update_model_acceptance_policy_status,
    update_model_ood_policy,
    update_model_status,
)

router = APIRouter(prefix="/ai/models", tags=["ai-modeling"])


@router.get("", response_model=list[ModelVersionRead])
def list_models(db: Session = Depends(get_db)) -> list[ModelVersion]:
    return list(db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())))


@router.get("/validation-folds", response_model=list[ModelValidationFoldRead])
def list_validation_folds(
    model_version_id: str | None = None, db: Session = Depends(get_db)
) -> list[ModelValidationFold]:
    query = select(ModelValidationFold)
    if model_version_id:
        query = query.where(ModelValidationFold.model_version_id == model_version_id)
    return list(
        db.scalars(
            query.order_by(
                ModelValidationFold.validation_axis,
                ModelValidationFold.fold_key,
            )
        )
    )


@router.get("/artifacts", response_model=list[ModelArtifactRead])
def list_model_artifacts(
    model_version_id: str | None = None, db: Session = Depends(get_db)
) -> list[ModelArtifact]:
    query = select(ModelArtifact)
    if model_version_id:
        query = query.where(ModelArtifact.model_version_id == model_version_id)
    return list(db.scalars(query.order_by(ModelArtifact.registered_at.desc())))


@router.get("/datasets", response_model=list[DatasetSnapshotRead])
def list_datasets(db: Session = Depends(get_db)) -> list[DatasetSnapshot]:
    return list(db.scalars(select(DatasetSnapshot).order_by(DatasetSnapshot.created_at.desc())))


@router.post("/datasets", response_model=DatasetSnapshotRead, status_code=status.HTTP_201_CREATED)
def build_dataset(
    payload: DatasetBuildRequest, db: Session = Depends(get_db)
) -> DatasetSnapshot:
    return build_dataset_snapshot(db, payload)


@router.get("/datasets/{dataset_snapshot_id}/members", response_model=list[DatasetSplitMemberRead])
def list_dataset_members(
    dataset_snapshot_id: str, db: Session = Depends(get_db)
) -> list[DatasetSplitMember]:
    if not db.get(DatasetSnapshot, dataset_snapshot_id):
        raise HTTPException(status_code=404, detail="数据集快照不存在")
    return list(
        db.scalars(
            select(DatasetSplitMember)
            .where(DatasetSplitMember.dataset_snapshot_id == dataset_snapshot_id)
            .order_by(DatasetSplitMember.occurred_at, DatasetSplitMember.measurement_point_id)
        )
    )


@router.get("/acceptance-decisions", response_model=list[ModelAcceptanceDecisionRead])
def list_acceptance_decisions(db: Session = Depends(get_db)) -> list[ModelAcceptanceDecision]:
    return list(
        db.scalars(
            select(ModelAcceptanceDecision).order_by(ModelAcceptanceDecision.decided_at.desc())
        )
    )


@router.get("/feature-snapshots")
def list_feature_snapshots(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(
            PointFeatureSnapshot,
            ProductionRun,
            MeasurementPoint,
            Factory,
            VehicleModel,
            Color,
        )
        .join(ProductionRun, ProductionRun.id == PointFeatureSnapshot.production_run_id)
        .join(MeasurementPoint, MeasurementPoint.id == PointFeatureSnapshot.measurement_point_id)
        .join(Factory, Factory.id == ProductionRun.factory_id)
        .join(VehicleModel, VehicleModel.id == ProductionRun.vehicle_model_id)
        .join(Color, Color.id == ProductionRun.color_id)
        .where(PointFeatureSnapshot.feature_set_version == CURRENT_FEATURE_SET_VERSION)
        .order_by(PointFeatureSnapshot.generated_at.desc())
        .limit(500)
    ).all()
    return [
        {
            "id": snapshot.id,
            "production_run_id": snapshot.production_run_id,
            "production_run_no": run.run_no,
            "factory_id": run.factory_id,
            "factory_code": factory.code,
            "factory_name": factory.name,
            "vehicle_model_id": run.vehicle_model_id,
            "vehicle_model_code": vehicle_model.code,
            "vehicle_model_name": vehicle_model.name,
            "color_id": run.color_id,
            "color_code": color.code,
            "color_name": color.name,
            "measurement_point_id": snapshot.measurement_point_id,
            "measurement_point_code": point.code,
            "measurement_point_name": point.name,
            "feature_set_version": snapshot.feature_set_version,
            "target_family": snapshot.target_family,
            "lineage": snapshot.lineage,
            "feature_count": len(snapshot.feature_values),
            "completeness_score": snapshot.completeness_score,
            "generated_at": snapshot.generated_at,
        }
        for snapshot, run, point, factory, vehicle_model, color in rows
    ]


@router.post("/train", response_model=ModelVersionRead, status_code=status.HTTP_201_CREATED)
def train_baseline_model(
    payload: ModelTrainingRequest, db: Session = Depends(get_db)
) -> ModelVersion:
    return train_model(db, payload)


@router.get("/acceptance-policies")
def list_acceptance_policies(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(ModelAcceptancePolicy, Factory)
        .join(Factory, Factory.id == ModelAcceptancePolicy.factory_id)
        .order_by(ModelAcceptancePolicy.created_at.desc())
    ).all()
    return [
        {
            "id": policy.id,
            "policy_code": policy.policy_code,
            "version": policy.version,
            "factory_id": policy.factory_id,
            "factory_code": factory.code,
            "factory_name": factory.name,
            "target_metric": policy.target_metric,
            "policy_type": policy.policy_type,
            "max_validation_rmse": policy.max_validation_rmse,
            "min_validation_r2": policy.min_validation_r2,
            "min_train_groups": policy.min_train_groups,
            "min_validation_groups": policy.min_validation_groups,
            "status": policy.status,
            "source_uri": policy.source_uri,
            "approved_by": policy.approved_by,
            "approved_at": policy.approved_at,
            "remark": policy.remark,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        }
        for policy, factory in rows
    ]


@router.post(
    "/acceptance-policies",
    response_model=ModelAcceptancePolicyRead,
    status_code=status.HTTP_201_CREATED,
)
def add_acceptance_policy(
    payload: ModelAcceptancePolicyCreate,
    db: Session = Depends(get_db),
) -> ModelAcceptancePolicy:
    return create_model_acceptance_policy(db, payload)


@router.patch(
    "/acceptance-policies/{policy_id}/status",
    response_model=ModelAcceptancePolicyRead,
)
def change_acceptance_policy_status(
    policy_id: str,
    payload: ModelAcceptancePolicyStatusUpdate,
    db: Session = Depends(get_db),
) -> ModelAcceptancePolicy:
    policy = db.get(ModelAcceptancePolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="模型验收策略不存在")
    return update_model_acceptance_policy_status(db, policy, payload)


@router.get("/applicability-scopes")
def list_applicability_scopes(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(ModelApplicabilityScope, Factory, VehicleModel, Color)
        .join(Factory, Factory.id == ModelApplicabilityScope.factory_id)
        .join(VehicleModel, VehicleModel.id == ModelApplicabilityScope.vehicle_model_id)
        .join(Color, Color.id == ModelApplicabilityScope.color_id)
        .order_by(ModelApplicabilityScope.created_at.desc())
    ).all()
    return [
        {
            "id": scope.id,
            "model_version_id": scope.model_version_id,
            "factory_id": scope.factory_id,
            "factory_code": factory.code,
            "factory_name": factory.name,
            "vehicle_model_id": scope.vehicle_model_id,
            "vehicle_model_code": vehicle_model.code,
            "vehicle_model_name": vehicle_model.name,
            "color_id": scope.color_id,
            "color_code": color.code,
            "color_name": color.name,
            "status": scope.status,
            "source": scope.source,
            "approved_by": scope.approved_by,
            "approved_at": scope.approved_at,
            "remark": scope.remark,
            "created_at": scope.created_at,
            "updated_at": scope.updated_at,
        }
        for scope, factory, vehicle_model, color in rows
    ]


@router.post(
    "/{model_version_id}/applicability-scopes",
    response_model=ModelApplicabilityScopeRead,
    status_code=status.HTTP_201_CREATED,
)
def add_applicability_scope(
    model_version_id: str,
    payload: ModelApplicabilityScopeCreate,
    db: Session = Depends(get_db),
) -> ModelApplicabilityScope:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return create_model_applicability_scope(db, model, payload)


@router.patch(
    "/{model_version_id}/applicability-scopes/{scope_id}",
    response_model=ModelApplicabilityScopeRead,
)
def change_applicability_scope(
    model_version_id: str,
    scope_id: str,
    payload: ModelApplicabilityScopeStatusUpdate,
    db: Session = Depends(get_db),
) -> ModelApplicabilityScope:
    model = db.get(ModelVersion, model_version_id)
    scope = db.get(ModelApplicabilityScope, scope_id)
    if not model or not scope or scope.model_version_id != model.id:
        raise HTTPException(status_code=404, detail="模型适用范围不存在")
    return update_model_applicability_scope(db, model, scope, payload)


@router.get("/ood-policies", response_model=list[ModelOodPolicyRead])
def list_ood_policies(db: Session = Depends(get_db)) -> list[ModelOodPolicy]:
    return list(db.scalars(select(ModelOodPolicy).order_by(ModelOodPolicy.created_at.desc())))


@router.put("/{model_version_id}/ood-policy", response_model=ModelOodPolicyRead)
def change_ood_policy(
    model_version_id: str,
    payload: ModelOodPolicyUpdate,
    db: Session = Depends(get_db),
) -> ModelOodPolicy:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return update_model_ood_policy(db, model, payload)


@router.post(
    "/{model_version_id}/governance-check",
    response_model=ModelGovernanceCheckResponse,
)
def check_model_governance(
    model_version_id: str,
    payload: ModelGovernanceCheckRequest,
    db: Session = Depends(get_db),
) -> dict:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    result = model_governance_check(
        db, model, payload.production_run_id, payload.measurement_point_id
    )
    result.pop("_snapshot", None)
    return result


@router.post(
    "/{model_version_id}/acceptance",
    response_model=ModelAcceptanceDecisionRead,
    status_code=status.HTTP_201_CREATED,
)
def decide_model_acceptance(
    model_version_id: str,
    payload: ModelAcceptanceRequest,
    db: Session = Depends(get_db),
) -> ModelAcceptanceDecision:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return record_model_acceptance(db, model, payload)


@router.get("/{model_version_id}/drift", response_model=ModelDriftReport)
def get_model_drift(model_version_id: str, db: Session = Depends(get_db)) -> dict:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return model_drift_report(db, model)


@router.patch("/{model_version_id}/status", response_model=ModelVersionRead)
def change_model_status(
    model_version_id: str,
    payload: ModelStatusUpdate,
    db: Session = Depends(get_db),
) -> ModelVersion:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return update_model_status(db, model, payload.status)


@router.post("/{model_version_id}/predictions", response_model=ModelPredictionResponse)
def predict_from_snapshot(
    model_version_id: str,
    payload: ModelPredictionRequest,
    db: Session = Depends(get_db),
) -> dict:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    if model.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="只有生效模型可以执行在线预测")
    return predict_with_model(
        db,
        model,
        production_run_id=payload.production_run_id,
        measurement_point_id=payload.measurement_point_id,
        persist_result=payload.persist_result,
    )


@router.post(
    "/predictions/{prediction_result_id}/diagnoses",
    response_model=ModelDiagnosisResponse,
)
def diagnose_from_prediction(
    prediction_result_id: str, db: Session = Depends(get_db)
) -> dict:
    prediction = db.get(PredictionResult, prediction_result_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="预测结果不存在")
    diagnosis = diagnose_prediction(db, prediction)
    return {
        "diagnosis_result_id": diagnosis.id,
        "prediction_result_id": prediction.id,
        "metric_code": diagnosis.metric_code,
        "summary": diagnosis.summary,
        "confidence": diagnosis.confidence,
        "causality_status": diagnosis.causality_status,
        "factor_contributions": diagnosis.factor_contributions,
    }


@router.post(
    "/{model_version_id}/recommendations",
    response_model=ModelRecommendationResponse,
    status_code=status.HTTP_201_CREATED,
)
def recommend_from_snapshot(
    model_version_id: str,
    payload: ModelRecommendationRequest,
    db: Session = Depends(get_db),
) -> dict:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    if model.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="只有生效模型可以生成工艺推荐")
    return recommend_with_model(
        db,
        model,
        production_run_id=payload.production_run_id,
        measurement_point_id=payload.measurement_point_id,
        target_min=payload.target_min,
        target_max=payload.target_max,
        max_actions=payload.max_actions,
        max_step_ratio=payload.max_step_ratio,
    )
