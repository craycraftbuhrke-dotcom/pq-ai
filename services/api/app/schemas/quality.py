from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.master_data import ResourceRead


class QualityMetricInput(BaseModel):
    metric_code: str = Field(min_length=1, max_length=64)
    metric_name: str = Field(min_length=1, max_length=120)
    raw_value: float
    corrected_value: float | None = None
    unit: str | None = Field(default=None, max_length=24)


class QualityMetricDefinitionRead(ResourceRead):
    quality_type: str
    code: str
    name: str
    unit: str | None
    display_order: int
    is_primary: bool


class QualityMeasurementCreate(BaseModel):
    data_no: str = Field(min_length=1, max_length=64)
    production_run_id: str
    measurement_group_id: str | None = None
    measurement_point_id: str
    quality_type: str
    data_type: str = Field(default="TEST", max_length=24)
    measured_at: datetime
    measured_by: str | None = Field(default=None, max_length=80)
    device_code: str | None = Field(default=None, max_length=64)
    status_score: float | None = None
    is_valid: bool = True
    metrics: list[QualityMetricInput] = Field(min_length=1)


class QualityMeasurementUpdate(BaseModel):
    data_no: str | None = Field(default=None, min_length=1, max_length=64)
    production_run_id: str | None = None
    measurement_group_id: str | None = None
    measurement_point_id: str | None = None
    quality_type: str | None = None
    data_type: str | None = Field(default=None, max_length=24)
    measured_at: datetime | None = None
    measured_by: str | None = Field(default=None, max_length=80)
    device_code: str | None = Field(default=None, max_length=64)
    status_score: float | None = None
    is_valid: bool | None = None
    metrics: list[QualityMetricInput] | None = Field(default=None, min_length=1)


class QualityMetricRead(QualityMetricInput, ResourceRead):
    measurement_id: str


class QualityMeasurementRead(ResourceRead):
    data_no: str
    production_run_id: str
    measurement_group_id: str | None
    measurement_point_id: str
    measurement_point_code: str
    measurement_point_name: str
    quality_type: str
    data_type: str
    measured_at: datetime
    measured_by: str | None
    device_code: str | None
    status_score: float | None
    is_valid: bool
    judgement: str
    violations: list[str]
    metrics: list[QualityMetricRead]


class QualityStandardCreate(BaseModel):
    standard_no: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    standard_type: str = Field(default="PRODUCTION", max_length=24)
    quality_type: str
    metric_code: str = Field(min_length=1, max_length=64)
    vehicle_model_id: str | None = None
    color_id: str | None = None
    part_id: str | None = None
    measurement_point_id: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = Field(default=None, max_length=24)
    is_active: bool = True


class QualityStandardUpdate(BaseModel):
    standard_no: str | None = Field(default=None, min_length=1, max_length=64)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    standard_type: str | None = Field(default=None, max_length=24)
    quality_type: str | None = None
    metric_code: str | None = Field(default=None, min_length=1, max_length=64)
    vehicle_model_id: str | None = None
    color_id: str | None = None
    part_id: str | None = None
    measurement_point_id: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = Field(default=None, max_length=24)
    is_active: bool | None = None


class QualityStandardRead(QualityStandardCreate, ResourceRead):
    pass


class QualitySummary(BaseModel):
    measurements: int
    valid_measurements: int
    metric_values: int
    standards: int
    pass_measurements: int
    fail_measurements: int
    no_standard_measurements: int
    measurements_by_type: dict[str, int]
