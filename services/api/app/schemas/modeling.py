from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.scope_policy import CURRENT_FEATURE_SET_VERSION


class DatasetBuildRequest(BaseModel):
    dataset_code: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    target_metric: str = Field(min_length=1, max_length=64)
    feature_set_version: str = Field(default=CURRENT_FEATURE_SET_VERSION, max_length=64)
    holdout_ratio: float = Field(default=0.25, ge=0.1, le=0.5)
    min_train_groups: int = Field(default=3, ge=2)
    min_validation_groups: int = Field(default=2, ge=1)


class DatasetSnapshotRead(BaseModel):
    id: str
    dataset_code: str
    version: str
    target_metric: str
    feature_set_version: str
    split_strategy: str
    group_key: str
    holdout_ratio: float
    status: str
    sample_count: int
    group_count: int
    train_sample_count: int
    validation_sample_count: int
    train_group_count: int
    validation_group_count: int
    cutoff_at: datetime | None
    feature_names: list[str]
    lineage: dict
    leakage_check: dict
    built_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetSplitMemberRead(BaseModel):
    id: str
    dataset_snapshot_id: str
    point_feature_snapshot_id: str
    production_run_id: str
    measurement_point_id: str
    target_measurement_id: str
    group_value: str
    split: str
    target_value: float
    feature_values: dict
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelTrainingRequest(BaseModel):
    model_code: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    target_metric: str = Field(min_length=1, max_length=64)
    feature_set_version: str = Field(default=CURRENT_FEATURE_SET_VERSION, max_length=64)
    dataset_snapshot_id: str
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
    dataset_snapshot_id: str | None
    evaluation_metrics: dict
    training_sample_count: int
    trained_at: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "RETIRED", "DRAFT"]


class ModelAcceptanceRequest(BaseModel):
    decision: Literal["ACCEPTED", "REJECTED"]
    decided_by: str = Field(min_length=1, max_length=80)
    comment: str | None = Field(default=None, max_length=1000)
    max_validation_rmse: float | None = Field(default=None, gt=0)
    min_validation_r2: float | None = None


class ModelAcceptanceDecisionRead(BaseModel):
    id: str
    model_version_id: str
    dataset_snapshot_id: str
    decision: str
    criteria: dict
    checks: dict
    decided_by: str
    decided_at: datetime
    comment: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    validation_rmse: float | None
    baseline_rmse: float | None
    baseline_source: str
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
