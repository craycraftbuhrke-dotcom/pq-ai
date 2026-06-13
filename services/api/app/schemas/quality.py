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


class MeasurementInstrumentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    manufacturer: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    instrument_type: str = Field(
        pattern="^(BYK_COLOR|BYK_ORANGE_PEEL|FISCHER_THICKNESS)$"
    )
    serial_no: str = Field(min_length=1, max_length=120)
    firmware_version: str | None = Field(default=None, max_length=64)
    supported_quality_types: list[str] = Field(min_length=1)
    calibration_required: bool = True
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|MAINTENANCE|RETIRED)$")
    remark: str | None = None


class MeasurementInstrumentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    manufacturer: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    instrument_type: str | None = Field(
        default=None,
        pattern="^(BYK_COLOR|BYK_ORANGE_PEEL|FISCHER_THICKNESS)$",
    )
    serial_no: str | None = Field(default=None, min_length=1, max_length=120)
    firmware_version: str | None = Field(default=None, max_length=64)
    supported_quality_types: list[str] | None = Field(default=None, min_length=1)
    calibration_required: bool | None = None
    status: str | None = Field(
        default=None, pattern="^(ACTIVE|MAINTENANCE|RETIRED)$"
    )
    remark: str | None = None


class MeasurementInstrumentRead(MeasurementInstrumentCreate, ResourceRead):
    pass


class MeasurementMethodCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=32)
    quality_type: str
    instrument_type: str = Field(
        pattern="^(BYK_COLOR|BYK_ORANGE_PEEL|FISCHER_THICKNESS)$"
    )
    method_type: str = Field(min_length=1, max_length=64)
    probe_code: str | None = Field(default=None, max_length=64)
    substrate_type: str | None = Field(default=None, max_length=80)
    geometry_class: str | None = Field(default=None, max_length=80)
    layer_scope: str | None = Field(default=None, max_length=80)
    requires_reference: bool = False
    requires_direction: bool = False
    minimum_repeats: int = Field(default=1, ge=1, le=50)
    is_active: bool = True
    instructions: str | None = None


class MeasurementMethodUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    quality_type: str | None = None
    instrument_type: str | None = Field(
        default=None,
        pattern="^(BYK_COLOR|BYK_ORANGE_PEEL|FISCHER_THICKNESS)$",
    )
    method_type: str | None = Field(default=None, min_length=1, max_length=64)
    probe_code: str | None = Field(default=None, max_length=64)
    substrate_type: str | None = Field(default=None, max_length=80)
    geometry_class: str | None = Field(default=None, max_length=80)
    layer_scope: str | None = Field(default=None, max_length=80)
    requires_reference: bool | None = None
    requires_direction: bool | None = None
    minimum_repeats: int | None = Field(default=None, ge=1, le=50)
    is_active: bool | None = None
    instructions: str | None = None


class MeasurementMethodRead(MeasurementMethodCreate, ResourceRead):
    pass


class MeasurementReferenceStandardCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    quality_type: str
    serial_no: str | None = Field(default=None, max_length=120)
    certificate_no: str | None = Field(default=None, max_length=120)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    reference_values: dict | None = None
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|EXPIRED|RETIRED)$")
    remark: str | None = None


class MeasurementReferenceStandardUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    quality_type: str | None = None
    serial_no: str | None = Field(default=None, max_length=120)
    certificate_no: str | None = Field(default=None, max_length=120)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    reference_values: dict | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|EXPIRED|RETIRED)$")
    remark: str | None = None


class MeasurementReferenceStandardRead(MeasurementReferenceStandardCreate, ResourceRead):
    pass


class MeasurementImportProfileCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=32)
    instrument_type: str = Field(
        pattern="^(BYK_COLOR|BYK_ORANGE_PEEL|FISCHER_THICKNESS)$"
    )
    quality_type: str
    schema_version: str = Field(min_length=1, max_length=64)
    field_mapping: dict
    is_active: bool = True
    remark: str | None = None


class MeasurementImportProfileUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    instrument_type: str | None = Field(
        default=None,
        pattern="^(BYK_COLOR|BYK_ORANGE_PEEL|FISCHER_THICKNESS)$",
    )
    quality_type: str | None = None
    schema_version: str | None = Field(default=None, min_length=1, max_length=64)
    field_mapping: dict | None = None
    is_active: bool | None = None
    remark: str | None = None


class MeasurementImportProfileRead(MeasurementImportProfileCreate, ResourceRead):
    pass


class MeasurementCalibrationCreate(BaseModel):
    calibration_no: str = Field(min_length=1, max_length=64)
    instrument_id: str
    method_id: str | None = None
    reference_standard_id: str | None = None
    calibrated_at: datetime
    valid_until: datetime
    result: str = Field(pattern="^(PASS|FAIL)$")
    performed_by: str = Field(min_length=1, max_length=80)
    certificate_uri: str | None = Field(default=None, max_length=500)
    check_values: dict | None = None
    remark: str | None = None


class MeasurementCalibrationUpdate(BaseModel):
    calibration_no: str | None = Field(default=None, min_length=1, max_length=64)
    instrument_id: str | None = None
    method_id: str | None = None
    reference_standard_id: str | None = None
    calibrated_at: datetime | None = None
    valid_until: datetime | None = None
    result: str | None = Field(default=None, pattern="^(PASS|FAIL)$")
    performed_by: str | None = Field(default=None, min_length=1, max_length=80)
    certificate_uri: str | None = Field(default=None, max_length=500)
    check_values: dict | None = None
    remark: str | None = None


class MeasurementCalibrationRead(MeasurementCalibrationCreate, ResourceRead):
    pass


class MeasurementRepeatInput(BaseModel):
    repeat_no: int = Field(ge=1)
    metric_code: str = Field(min_length=1, max_length=64)
    raw_value: float
    corrected_value: float | None = None
    unit: str | None = Field(default=None, max_length=24)
    is_valid: bool = True
    invalid_reason: str | None = Field(default=None, max_length=240)


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
    instrument_id: str | None = None
    measurement_method_id: str | None = None
    calibration_record_id: str | None = None
    reference_standard_id: str | None = None
    import_profile_id: str | None = None
    measurement_direction: str | None = Field(default=None, max_length=32)
    raw_file_uri: str | None = Field(default=None, max_length=500)
    status_score: float | None = None
    is_valid: bool = True
    metrics: list[QualityMetricInput] = Field(min_length=1)
    repeat_readings: list[MeasurementRepeatInput] = Field(default_factory=list)


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
    instrument_id: str | None = None
    measurement_method_id: str | None = None
    calibration_record_id: str | None = None
    reference_standard_id: str | None = None
    import_profile_id: str | None = None
    measurement_direction: str | None = Field(default=None, max_length=32)
    raw_file_uri: str | None = Field(default=None, max_length=500)
    status_score: float | None = None
    is_valid: bool | None = None
    metrics: list[QualityMetricInput] | None = Field(default=None, min_length=1)
    repeat_readings: list[MeasurementRepeatInput] | None = None


class QualityMetricRead(QualityMetricInput, ResourceRead):
    measurement_id: str


class MeasurementRepeatRead(MeasurementRepeatInput, ResourceRead):
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
    instrument_id: str | None
    instrument_code: str | None
    instrument_name: str | None
    measurement_method_id: str | None
    measurement_method_code: str | None
    calibration_record_id: str | None
    calibration_no: str | None
    reference_standard_id: str | None
    reference_standard_code: str | None
    import_profile_id: str | None
    import_profile_code: str | None
    measurement_direction: str | None
    raw_file_uri: str | None
    reliability_status: str
    reliability_issues: list[str]
    status_score: float | None
    is_valid: bool
    judgement: str
    violations: list[str]
    metrics: list[QualityMetricRead]
    repeat_readings: list[MeasurementRepeatRead]


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
    verified_measurements: int
    unverified_measurements: int
    failed_reliability_measurements: int
    measurements_by_type: dict[str, int]


class QualityAnalyticsSeriesPoint(BaseModel):
    measurement_id: str
    data_no: str
    measurement_point_id: str
    measurement_point_code: str
    measurement_point_name: str
    measured_at: datetime
    value: float
    judgement: str
    standard_min: float | None
    standard_max: float | None


class QualityAnalyticsStatistics(BaseModel):
    samples: int
    mean: float | None
    sigma: float | None
    minimum: float | None
    maximum: float | None
    ucl: float | None
    lcl: float | None
    trend_slope: float | None
    cp: float | None
    cpk: float | None
    pass_rate: float
    out_of_control_count: int


class QualityPointRisk(BaseModel):
    measurement_point_id: str
    measurement_point_code: str
    measurement_point_name: str
    samples: int
    failures: int
    fail_rate: float
    no_standard_count: int
    latest_value: float
    latest_judgement: str
    risk_score: float


class QualityDataQuality(BaseModel):
    total_measurements: int
    valid_measurements: int
    invalid_measurements: int
    measurements_with_metric: int
    missing_metric_count: int
    no_standard_count: int
    valid_rate: float
    metric_completeness: float
    standard_coverage: float
    latest_measured_at: datetime | None


class QualityAnalytics(BaseModel):
    quality_type: str
    metric_code: str
    metric_name: str
    unit: str | None
    statistics: QualityAnalyticsStatistics
    data_quality: QualityDataQuality
    series: list[QualityAnalyticsSeriesPoint]
    point_risks: list[QualityPointRisk]
