from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.scope_policy import CURRENT_FEATURE_SET_VERSION


class PointFeatureBuildRequest(BaseModel):
    production_run_id: str
    measurement_point_id: str
    feature_set_version: str = Field(default=CURRENT_FEATURE_SET_VERSION, max_length=64)


class PointFeatureResult(BaseModel):
    snapshot_id: str
    production_run_id: str
    measurement_point_id: str
    feature_set_version: str
    feature_values: dict[str, float]
    quality_labels: dict[str, float]
    completeness_score: float
    generated_at: datetime
    stage_coverage: list[str]
    contribution_count: int
