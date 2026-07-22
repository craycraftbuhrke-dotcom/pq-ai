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
    calibration_required: bool = False
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
    measurement_probe_id: str | None = None
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
    measurement_probe_id: str | None = None
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
    measurement_probe_id: str | None
    measurement_probe_code: str | None
    measurement_probe_name: str | None
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


class BodyMapLayoutUpsert(BaseModel):
    body_view: str = Field(pattern="^(TOP|SIDE|LEFT|RIGHT|REAR)$")
    layout_x: float = Field(ge=0, le=1)
    layout_y: float = Field(ge=0, le=1)
    grid_col: int | None = Field(default=None, ge=0)
    grid_row: int | None = Field(default=None, ge=0)


class BodyMapLayoutRead(BodyMapLayoutUpsert, ResourceRead):
    measurement_point_id: str
    status: str


class BodyMapPointCreate(BaseModel):
    vehicle_model_id: str
    body_view: str = Field(pattern="^(TOP|SIDE|LEFT|RIGHT|REAR)$")
    layout_x: float = Field(ge=0, le=1)
    layout_y: float = Field(ge=0, le=1)
    grid_col: int | None = Field(default=None, ge=0)
    grid_row: int | None = Field(default=None, ge=0)
    code: str = Field(min_length=1, max_length=48)
    name: str = Field(min_length=1, max_length=120)
    part_id: str
    region: str | None = Field(default=None, max_length=80)
    quality_types: list[str] = Field(
        default_factory=lambda: ["ORANGE_PEEL", "COLOR_DIFFERENCE", "THICKNESS"]
    )
    measurement_group_id: str | None = None
    point_type: str = Field(default="QUALITY", max_length=32)
    # 可选：与喷涂刷子建立贡献关联（刷子表/刷子号对应 Brush）
    brush_id: str | None = None
    overlap_ratio: float = Field(default=1.0, ge=0, le=1)
    contribution_weight: float = Field(default=1.0, gt=0, le=1)


class BodyMapLayoutDeactivate(BaseModel):
    body_view: str = Field(pattern="^(TOP|SIDE|LEFT|RIGHT|REAR)$")


class BodyMapMetricReading(BaseModel):
    metric_code: str
    metric_name: str | None = None
    value: float | None = None
    unit: str | None = None
    judgement: str | None = None
    is_primary: bool = False


class BodyMapQualitySummary(BaseModel):
    quality_type: str
    metric_code: str | None = None
    metric_name: str | None = None
    value: float | None = None
    unit: str | None = None
    measured_at: datetime | None = None
    data_no: str | None = None
    judgement: str | None = None
    reliability_status: str | None = None
    metrics: list[BodyMapMetricReading] = Field(default_factory=list)


class BodyMapPointItem(BaseModel):
    measurement_point_id: str
    layout_id: str | None = None
    code: str
    name: str
    part_id: str
    part_code: str | None = None
    part_name: str | None = None
    region: str | None = None
    quality_types: list[str] = Field(default_factory=list)
    layout_x: float | None = None
    layout_y: float | None = None
    grid_col: int | None = None
    grid_row: int | None = None
    in_group: bool = False
    quality_summaries: list[BodyMapQualitySummary] = Field(default_factory=list)
    risk_score: float = 0


class BodyMapResponse(BaseModel):
    vehicle_model_id: str
    vehicle_model_code: str
    vehicle_model_name: str
    body_view: str
    background_image_url: str
    grid_cols: int
    grid_rows: int
    measurement_group_id: str | None = None
    production_run_id: str | None = None
    production_run_no: str | None = None
    quality_scope: str = "VERIFIED"
    placed_count: int = 0
    group_point_count: int = 0
    fail_count: int = 0
    points: list[BodyMapPointItem]


class BodyMapCanvasResponse(BaseModel):
    vehicle_model_id: str
    vehicle_model_code: str
    vehicle_model_name: str
    view_order: list[str]
    view_labels: dict[str, str]
    grid_cols: int
    grid_rows: int
    measurement_group_id: str | None = None
    production_run_id: str | None = None
    production_run_no: str | None = None
    quality_scope: str = "VERIFIED"
    placed_count: int = 0
    group_point_count: int = 0
    fail_count: int = 0
    views: list[BodyMapResponse]


class BodyMapBrushParameter(BaseModel):
    parameter_code: str
    parameter_name: str
    configured_value: float | None = None
    actual_value: float | None = None
    unit: str
    soft_min: float | None = None
    soft_max: float | None = None
    hard_min: float | None = None
    hard_max: float | None = None


class BodyMapBrushContribution(BaseModel):
    brush_id: str
    brush_no: str
    brush_table_no: str
    program_version_id: str | None = None
    program_version: str | None = None
    program_code: str | None = None
    program_name: str | None = None
    process_stage: str
    coating_system: str
    overlap_ratio: float
    contribution_weight: float
    source: str
    version: str
    is_approved: bool
    contribution_source: str = "LEGACY"
    target_family: str | None = None
    validation_score: float | None = None
    path_segment_id: str | None = None
    parameters: list[BodyMapBrushParameter] = Field(default_factory=list)


class BodyMapPointDetail(BaseModel):
    measurement_point_id: str
    code: str
    name: str
    part_id: str
    part_code: str | None = None
    part_name: str | None = None
    region: str | None = None
    quality_types: list[str] = Field(default_factory=list)
    quality_summaries: list[BodyMapQualitySummary] = Field(default_factory=list)
    brush_contributions: list[BodyMapBrushContribution] = Field(default_factory=list)


class BodyMap3DLayoutUpsert(BaseModel):
    pos_x: float
    pos_y: float
    pos_z: float
    normal_x: float | None = None
    normal_y: float | None = None
    normal_z: float | None = None
    model_asset_key: str | None = Field(default=None, max_length=120)
    project_to_2d: bool = Field(
        default=True,
        description="执行时是否同步生成二维投影；该指令不持久化到三维布局表",
    )


class BodyMap3DLayoutRead(ResourceRead):
    measurement_point_id: str
    pos_x: float
    pos_y: float
    pos_z: float
    normal_x: float | None = None
    normal_y: float | None = None
    normal_z: float | None = None
    model_asset_key: str | None = None
    status: str
    projected_views: dict[str, dict[str, float | bool]] = Field(default_factory=dict)
    projected_clamped: bool = False


class BodyMap3DPointItem(BaseModel):
    measurement_point_id: str
    layout_3d_id: str | None = None
    code: str
    name: str
    part_id: str
    part_code: str | None = None
    part_name: str | None = None
    region: str | None = None
    quality_types: list[str] = Field(default_factory=list)
    pos_x: float | None = None
    pos_y: float | None = None
    pos_z: float | None = None
    normal_x: float | None = None
    normal_y: float | None = None
    normal_z: float | None = None
    in_group: bool = False
    has_2d_only: bool = False
    quality_summaries: list[BodyMapQualitySummary] = Field(default_factory=list)
    risk_score: float = 0


class BodyMap3DSceneResponse(BaseModel):
    vehicle_model_id: str
    vehicle_model_code: str
    vehicle_model_name: str
    model_url: str | None = None
    model_asset_key: str | None = None
    up_axis: str = "Y"
    unit_scale: float = 1.0
    bounds: dict[str, float] = Field(default_factory=dict)
    measurement_group_id: str | None = None
    production_run_id: str | None = None
    production_run_no: str | None = None
    quality_scope: str = "VERIFIED"
    placed_count: int = 0
    group_point_count: int = 0
    fail_count: int = 0
    points: list[BodyMap3DPointItem] = Field(default_factory=list)
