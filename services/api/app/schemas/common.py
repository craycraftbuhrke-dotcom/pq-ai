from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FactoryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=120)
    site_owner: str | None = None
    remark: str | None = None


class FactoryUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    site_owner: str | None = None
    remark: str | None = None
    is_active: bool | None = None


class FactoryRead(FactoryCreate):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationApproval(BaseModel):
    approved: bool
    approved_by: str = Field(min_length=2, max_length=80)
    comment: str | None = Field(default=None, max_length=500)


class ControlledTrialCreate(BaseModel):
    hypothesis: str = Field(min_length=8, max_length=2000)
    evidence_type: Literal["ASSOCIATION", "RULE", "SIMULATION", "DOE", "CONTROLLED_CHANGE"] = (
        "ASSOCIATION"
    )
    expected_outcome: str = Field(min_length=4, max_length=1000)
    risk_assessment: str = Field(min_length=4, max_length=1000)
    rollback_plan: str = Field(min_length=4, max_length=1000)
    sustained_observation_plan: str = Field(min_length=4, max_length=1000)
    requested_by: str = Field(min_length=2, max_length=80)


class ControlledTrialApproval(BaseModel):
    approved: bool
    approved_by: str = Field(min_length=2, max_length=80)
    comment: str | None = Field(default=None, max_length=1000)


class RollbackExecutionCreate(BaseModel):
    rollback_reason: str = Field(min_length=4, max_length=1000)
    executed_by: str = Field(min_length=2, max_length=80)
    rollback_to_program_version_id: str | None = None
    execution_note: str | None = Field(default=None, max_length=1000)


class RecommendationExecutionAction(BaseModel):
    action_id: str
    executed_value: float


class RecommendationExecution(BaseModel):
    executed_by: str = Field(min_length=2, max_length=80)
    actions: list[RecommendationExecutionAction] = Field(min_length=1)


class RecommendationVerification(BaseModel):
    verified_measurement_id: str
    verified_by: str = Field(min_length=2, max_length=80)
    conclusion: str | None = Field(default=None, max_length=1000)


class PredictionRequest(BaseModel):
    production_run_no: str
    measurement_point_code: str
    target_metrics: list[str] = Field(default_factory=lambda: ["thickness_total", "doi"])


class DiagnosisRequest(BaseModel):
    production_run_no: str
    measurement_point_code: str
    observed_metric: str
    observed_value: float


class RecommendationRequest(BaseModel):
    production_run_no: str
    measurement_point_code: str
    target_metric: str
    target_min: float | None = None
    target_max: float | None = None
