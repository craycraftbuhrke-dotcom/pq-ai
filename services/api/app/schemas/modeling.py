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
    include_all_production: bool = True
    production_snapshot_ids: list[str] = Field(default_factory=list, max_length=5000)
    manual_upload_ids: list[str] = Field(default_factory=list, max_length=500)


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
    source_type: str
    source_ref: str
    point_feature_snapshot_id: str | None
    manual_sample_id: str | None
    production_run_id: str | None
    measurement_point_id: str | None
    target_measurement_id: str | None
    group_value: str
    split: str
    target_value: float
    feature_values: dict
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingDataUploadRead(BaseModel):
    id: str
    upload_no: str
    name: str
    target_metric: str
    feature_set_version: str
    source_type: str
    file_name: str
    file_hash: str
    status: str
    sample_count: int
    feature_names: list[str]
    validation_report: dict
    uploaded_by: str
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingWideSampleRead(BaseModel):
    id: str
    upload_id: str
    sample_no: str
    group_value: str
    factory_id: str | None = None
    vehicle_model_id: str | None = None
    color_id: str | None = None
    occurred_at: datetime
    target_value: float
    feature_values: dict
    lineage: dict
    is_valid: bool

    model_config = ConfigDict(from_attributes=True)


class ModelTrainingRequest(BaseModel):
    model_code: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    target_metric: str = Field(min_length=1, max_length=64)
    feature_set_version: str = Field(default=CURRENT_FEATURE_SET_VERSION, max_length=64)
    dataset_snapshot_id: str
    min_samples: int = Field(default=5, ge=3)
    model_family: Literal["AUTO", "RIDGE", "ELASTIC_NET"] = "AUTO"
    ridge_lambda: float = Field(default=0.1, ge=0)
    elastic_net_l1_ratio: float = Field(default=0.5, ge=0.05, le=0.95)
    max_abs_standardized_shift: float = Field(default=4.0, gt=0)
    max_outlier_feature_ratio: float = Field(default=0.2, ge=0, le=1)
    min_feature_completeness: float = Field(default=1.0, gt=0, le=1)


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


class AvailableModelRead(BaseModel):
    id: str
    model_code: str
    version: str
    model_type: str
    target_metric: str
    target_name: str
    allowed: bool
    applicability_status: str
    ood_status: str
    reason: str | None = None


class ModelValidationFoldRead(BaseModel):
    id: str
    model_version_id: str
    dataset_snapshot_id: str
    validation_axis: str
    fold_key: str
    train_sample_count: int
    validation_sample_count: int
    train_group_count: int
    validation_group_count: int
    metrics: dict
    status: str
    evaluated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelArtifactRead(BaseModel):
    id: str
    model_version_id: str
    artifact_type: str
    artifact_uri: str
    storage_backend: str
    payload_hash: str
    metadata_payload: dict
    status: str
    created_by: str
    registered_at: datetime
    remark: str | None
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


class ModelAcceptancePolicyCreate(BaseModel):
    policy_code: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    factory_id: str
    target_metric: str = Field(min_length=1, max_length=64)
    max_validation_rmse: float = Field(gt=0)
    min_validation_r2: float
    min_train_groups: int = Field(default=3, ge=2)
    min_validation_groups: int = Field(default=2, ge=1)
    source_uri: str = Field(min_length=1, max_length=500)
    remark: str | None = Field(default=None, max_length=1000)


class ModelAcceptancePolicyStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "RETIRED", "DRAFT"]
    approved_by: str | None = Field(default=None, max_length=80)


class ModelAcceptancePolicyRead(BaseModel):
    id: str
    policy_code: str
    version: str
    factory_id: str
    target_metric: str
    policy_type: str
    max_validation_rmse: float
    min_validation_r2: float
    min_train_groups: int
    min_validation_groups: int
    status: str
    source_uri: str
    approved_by: str | None
    approved_at: datetime | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelApplicabilityScopeCreate(BaseModel):
    factory_id: str
    vehicle_model_id: str
    color_id: str
    remark: str | None = Field(default=None, max_length=1000)


class ModelApplicabilityScopeStatusUpdate(BaseModel):
    status: Literal["PENDING", "INACTIVE"]
    remark: str | None = Field(default=None, max_length=1000)


class ModelApplicabilityScopeRead(BaseModel):
    id: str
    model_version_id: str
    factory_id: str
    vehicle_model_id: str
    color_id: str
    status: str
    source: str
    approved_by: str | None
    approved_at: datetime | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelOodPolicyUpdate(BaseModel):
    max_abs_standardized_shift: float = Field(gt=0)
    max_outlier_feature_ratio: float = Field(ge=0, le=1)
    min_feature_completeness: float = Field(gt=0, le=1)
    action: Literal["BLOCK"] = "BLOCK"
    remark: str | None = Field(default=None, max_length=1000)


class ModelOodPolicyRead(BaseModel):
    id: str
    model_version_id: str
    max_abs_standardized_shift: float
    max_outlier_feature_ratio: float
    min_feature_completeness: float
    action: str
    status: str
    approved_by: str | None
    approved_at: datetime | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelGovernanceCheckRequest(BaseModel):
    production_run_id: str
    measurement_point_id: str


class ModelGovernanceCheckResponse(BaseModel):
    model_version_id: str
    production_run_id: str
    measurement_point_id: str
    allowed: bool
    applicability_status: str
    ood_status: str
    evidence: dict


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
    model_type: str
    predicted_value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    uncertainty_source: str
    feature_completeness: float
    applicability_status: str
    ood_status: str
    governance_evidence: dict


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
    target_min: float | None
    target_max: float | None
    target_source: str
    current_prediction: float
    expected_prediction: float
    predicted_improvement: float
    confidence: float
    constraints_checked: bool
    actions: list[dict]
