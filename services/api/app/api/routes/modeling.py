from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import MeasurementPoint, ModelVersion, PointFeatureSnapshot, PredictionResult, ProductionRun
from app.schemas.modeling import (
    ModelDiagnosisResponse,
    ModelPredictionRequest,
    ModelPredictionResponse,
    ModelRecommendationRequest,
    ModelRecommendationResponse,
    ModelTrainingRequest,
    ModelVersionRead,
)
from app.services.modeling import (
    diagnose_prediction,
    predict_with_model,
    recommend_with_model,
    train_model,
)

router = APIRouter(prefix="/ai/models", tags=["ai-modeling"])


@router.get("", response_model=list[ModelVersionRead])
def list_models(db: Session = Depends(get_db)) -> list[ModelVersion]:
    return list(db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())))


@router.get("/feature-snapshots")
def list_feature_snapshots(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(PointFeatureSnapshot, ProductionRun, MeasurementPoint)
        .join(ProductionRun, ProductionRun.id == PointFeatureSnapshot.production_run_id)
        .join(MeasurementPoint, MeasurementPoint.id == PointFeatureSnapshot.measurement_point_id)
        .order_by(PointFeatureSnapshot.generated_at.desc())
        .limit(500)
    ).all()
    return [
        {
            "id": snapshot.id,
            "production_run_id": snapshot.production_run_id,
            "production_run_no": run.run_no,
            "measurement_point_id": snapshot.measurement_point_id,
            "measurement_point_code": point.code,
            "measurement_point_name": point.name,
            "feature_set_version": snapshot.feature_set_version,
            "feature_count": len(snapshot.feature_values),
            "completeness_score": snapshot.completeness_score,
            "generated_at": snapshot.generated_at,
        }
        for snapshot, run, point in rows
    ]


@router.post("/train", response_model=ModelVersionRead, status_code=status.HTTP_201_CREATED)
def train_baseline_model(
    payload: ModelTrainingRequest, db: Session = Depends(get_db)
) -> ModelVersion:
    return train_model(db, payload)


@router.post("/{model_version_id}/predictions", response_model=ModelPredictionResponse)
def predict_from_snapshot(
    model_version_id: str,
    payload: ModelPredictionRequest,
    db: Session = Depends(get_db),
) -> dict:
    model = db.get(ModelVersion, model_version_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
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
