from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelTrainingRequest(BaseModel):
    model_code: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    target_metric: str = Field(min_length=1, max_length=64)
    feature_set_version: str = Field(default="point-features-v1", max_length=64)
    min_samples: int = Field(default=5, ge=3)
    ridge_lambda: float = Field(default=0.1, ge=0)


class ModelVersionRead(BaseModel):
    id: str
    model_code: str
    version: str
    model_type: str
    target_metric: str
    feature_set_version: str
    artifact_uri: str
    evaluation_metrics: dict
    training_sample_count: int
    trained_at: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "RETIRED", "DRAFT"]


class ModelDriftReport(BaseModel):
    model_version_id: str
    model_code: str
    version: str
    target_metric: str
    model_status: str
    drift_status: str
    recommendation: str
    monitored_snapshot_count: int
    prediction_count: int
    labeled_prediction_count: int
    average_feature_completeness: float | None
    average_confidence: float | None
    training_rmse: float | None
    live_mae: float | None
    live_rmse: float | None
    rmse_ratio: float | None
    max_feature_shift: float | None
    window_started_at: datetime | None
    window_ended_at: datetime | None
    feature_drift: list[dict]


class ModelPredictionRequest(BaseModel):
    production_run_id: str
    measurement_point_id: str
    persist_result: bool = True


class ModelPredictionResponse(BaseModel):
    prediction_result_id: str | None
    model_version_id: str
    production_run_id: str
    measurement_point_id: str
    metric_code: str
    predicted_value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    feature_completeness: float


class ModelDiagnosisResponse(BaseModel):
    diagnosis_result_id: str
    prediction_result_id: str
    metric_code: str
    summary: str
    confidence: float
    causality_status: str
    factor_contributions: list[dict]


class ModelRecommendationRequest(BaseModel):
    production_run_id: str
    measurement_point_id: str
    target_min: float | None = None
    target_max: float | None = None
    max_actions: int = Field(default=3, ge=1, le=10)
    max_step_ratio: float = Field(default=0.1, gt=0, le=0.5)


class ModelRecommendationResponse(BaseModel):
    recommendation_id: str
    recommendation_no: str
    status: str
    metric_code: str
    current_prediction: float
    expected_prediction: float
    predicted_improvement: float
    confidence: float
    constraints_checked: bool
    actions: list[dict]
