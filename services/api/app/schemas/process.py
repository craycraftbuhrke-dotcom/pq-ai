from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.master_data import ResourceRead


class ParameterDefinitionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=32)
    unit: str = Field(max_length=24)
    aggregation_method: str = Field(default="WEIGHTED_AVERAGE", max_length=32)
    hard_min: float | None = None
    hard_max: float | None = None
    is_recommendable: bool = True


class ParameterDefinitionRead(ParameterDefinitionCreate, ResourceRead):
    pass


class ParameterConstraintSourceCreate(BaseModel):
    parameter_definition_id: str
    constraint_code: str = Field(min_length=1, max_length=96)
    version: str = Field(min_length=1, max_length=32)
    source_type: str = Field(min_length=1, max_length=32)
    lower_limit: float
    upper_limit: float
    unit: str = Field(min_length=1, max_length=24)
    factory_id: str | None = None
    process_stage: str | None = Field(default=None, max_length=32)
    source_uri: str | None = Field(default=None, max_length=500)
    status: str = Field(default="DRAFT", max_length=24)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class ParameterConstraintSourceUpdate(BaseModel):
    parameter_definition_id: str | None = None
    constraint_code: str | None = Field(default=None, min_length=1, max_length=96)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    source_type: str | None = Field(default=None, min_length=1, max_length=32)
    lower_limit: float | None = None
    upper_limit: float | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    factory_id: str | None = None
    process_stage: str | None = Field(default=None, max_length=32)
    source_uri: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=24)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class ParameterConstraintSourceRead(ParameterConstraintSourceCreate, ResourceRead):
    approved_at: datetime | None = None


class SprayProgramCreate(BaseModel):
    program_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    factory_id: str
    process_stage: str
    station_code: str = Field(min_length=1, max_length=32)
    station_name: str = Field(min_length=1, max_length=120)
    robot_model: str | None = Field(default=None, max_length=120)
    remark: str | None = None


class SprayProgramUpdate(BaseModel):
    program_code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    factory_id: str | None = None
    process_stage: str | None = None
    station_code: str | None = Field(default=None, min_length=1, max_length=32)
    station_name: str | None = Field(default=None, min_length=1, max_length=120)
    robot_model: str | None = Field(default=None, max_length=120)
    remark: str | None = None


class SprayProgramRead(SprayProgramCreate, ResourceRead):
    pass


class SprayProgramVersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=32)
    status: str = Field(default="DRAFT", max_length=24)
    source_type: str = Field(default="MANUAL", max_length=24)
    is_master_sample: bool = False
    vehicle_model_ids: list[str] = Field(default_factory=list)
    color_ids: list[str] = Field(default_factory=list)


class SprayProgramVersionUpdate(BaseModel):
    version: str | None = Field(default=None, min_length=1, max_length=32)
    status: str | None = Field(default=None, max_length=24)
    source_type: str | None = Field(default=None, max_length=24)
    is_master_sample: bool | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    vehicle_model_ids: list[str] | None = None
    color_ids: list[str] | None = None


class BrushCreate(BaseModel):
    brush_no: str = Field(min_length=1, max_length=32)
    brush_table_no: str = Field(min_length=1, max_length=64)
    spray_position: str | None = Field(default=None, max_length=120)
    part_id: str | None = None
    remark: str | None = None


class BrushUpdate(BaseModel):
    brush_no: str | None = Field(default=None, min_length=1, max_length=32)
    brush_table_no: str | None = Field(default=None, min_length=1, max_length=64)
    spray_position: str | None = Field(default=None, max_length=120)
    part_id: str | None = None
    remark: str | None = None


class BrushRead(BrushCreate, ResourceRead):
    program_version_id: str


class BrushParameterCreate(BaseModel):
    parameter_definition_id: str | None = None
    parameter_code: str = Field(min_length=1, max_length=64)
    parameter_name: str = Field(min_length=1, max_length=120)
    configured_value: float
    unit: str = Field(max_length=24)
    soft_min: float | None = None
    soft_max: float | None = None
    hard_min: float | None = None
    hard_max: float | None = None
    is_recommendable: bool = True


class BrushParameterUpdate(BaseModel):
    parameter_definition_id: str | None = None
    parameter_code: str | None = Field(default=None, min_length=1, max_length=64)
    parameter_name: str | None = Field(default=None, min_length=1, max_length=120)
    configured_value: float | None = None
    unit: str | None = Field(default=None, max_length=24)
    soft_min: float | None = None
    soft_max: float | None = None
    hard_min: float | None = None
    hard_max: float | None = None
    is_recommendable: bool | None = None


class BrushParameterRead(BrushParameterCreate, ResourceRead):
    brush_id: str


class BrushPointContributionUpsert(BaseModel):
    overlap_ratio: float = Field(ge=0, le=1)
    contribution_weight: float = Field(gt=0, le=1)
    source: str = Field(default="EXPERT", max_length=32)
    version: str = Field(default="1.0", max_length=32)
    is_approved: bool = False


class BrushPointContributionRead(BrushPointContributionUpsert, ResourceRead):
    brush_id: str
    measurement_point_id: str


class DurrRobotCreate(BaseModel):
    factory_id: str
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    serial_no: str = Field(min_length=1, max_length=120)
    controller_software_version: str | None = Field(default=None, max_length=80)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|MAINTENANCE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    remark: str | None = None


class DurrRobotUpdate(BaseModel):
    factory_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    serial_no: str | None = Field(default=None, min_length=1, max_length=120)
    controller_software_version: str | None = Field(default=None, max_length=80)
    status: str | None = Field(
        default=None, pattern="^(ACTIVE|MAINTENANCE|RETIRED)$"
    )
    source_uri: str | None = Field(default=None, max_length=500)
    remark: str | None = None


class DurrRobotRead(DurrRobotCreate, ResourceRead):
    pass


class DurrControllerCreate(BaseModel):
    factory_id: str
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    serial_no: str = Field(min_length=1, max_length=120)
    software_version: str | None = Field(default=None, max_length=80)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|MAINTENANCE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    remark: str | None = None


class DurrControllerUpdate(BaseModel):
    factory_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    serial_no: str | None = Field(default=None, min_length=1, max_length=120)
    software_version: str | None = Field(default=None, max_length=80)
    status: str | None = Field(
        default=None, pattern="^(ACTIVE|MAINTENANCE|RETIRED)$"
    )
    source_uri: str | None = Field(default=None, max_length=500)
    remark: str | None = None


class DurrControllerRead(DurrControllerCreate, ResourceRead):
    pass


class DurrAtomizerCreate(BaseModel):
    factory_id: str
    controller_id: str | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    serial_no: str = Field(min_length=1, max_length=120)
    bell_cup_type: str | None = Field(default=None, max_length=120)
    bell_cup_code: str | None = Field(default=None, max_length=120)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|MAINTENANCE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    remark: str | None = None


class DurrAtomizerUpdate(BaseModel):
    factory_id: str | None = None
    controller_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    serial_no: str | None = Field(default=None, min_length=1, max_length=120)
    bell_cup_type: str | None = Field(default=None, max_length=120)
    bell_cup_code: str | None = Field(default=None, max_length=120)
    status: str | None = Field(
        default=None, pattern="^(ACTIVE|MAINTENANCE|RETIRED)$"
    )
    source_uri: str | None = Field(default=None, max_length=500)
    remark: str | None = None


class DurrAtomizerRead(DurrAtomizerCreate, ResourceRead):
    pass


class ProgramDeviceConfigurationCreate(BaseModel):
    program_version_id: str
    robot_id: str
    atomizer_id: str
    controller_id: str
    configuration_version: str = Field(min_length=1, max_length=32)
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    effective_from: datetime | None = None
    remark: str | None = None


class ProgramDeviceConfigurationUpdate(BaseModel):
    program_version_id: str | None = None
    robot_id: str | None = None
    atomizer_id: str | None = None
    controller_id: str | None = None
    configuration_version: str | None = Field(default=None, min_length=1, max_length=32)
    status: str | None = Field(
        default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$"
    )
    source_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    effective_from: datetime | None = None
    remark: str | None = None


class ProgramDeviceConfigurationRead(ProgramDeviceConfigurationCreate, ResourceRead):
    approved_at: datetime | None


class TrajectoryProgramCreate(BaseModel):
    program_version_id: str
    trajectory_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=32)
    checksum: str = Field(min_length=1, max_length=128)
    coordinate_system: str | None = Field(default=None, max_length=80)
    tcp_name: str | None = Field(default=None, max_length=120)
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class TrajectoryProgramUpdate(BaseModel):
    program_version_id: str | None = None
    trajectory_code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    checksum: str | None = Field(default=None, min_length=1, max_length=128)
    coordinate_system: str | None = Field(default=None, max_length=80)
    tcp_name: str | None = Field(default=None, max_length=120)
    status: str | None = Field(
        default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$"
    )
    source_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class TrajectoryProgramRead(TrajectoryProgramCreate, ResourceRead):
    approved_at: datetime | None


class TrajectoryPathSegmentCreate(BaseModel):
    trajectory_program_id: str
    segment_no: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=160)
    brush_id: str | None = None
    part_id: str | None = None
    tcp_name: str | None = Field(default=None, max_length=120)
    configured_speed: float | None = Field(default=None, gt=0)
    speed_unit: str | None = Field(default=None, max_length=24)
    start_position: dict | None = None
    end_position: dict | None = None
    orientation: dict | None = None
    trigger_state: str = Field(default="ON", pattern="^(ON|OFF|PULSE)$")
    trigger_start_ms: float | None = None
    trigger_end_ms: float | None = None
    remark: str | None = None


class TrajectoryPathSegmentUpdate(BaseModel):
    trajectory_program_id: str | None = None
    segment_no: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    brush_id: str | None = None
    part_id: str | None = None
    tcp_name: str | None = Field(default=None, max_length=120)
    configured_speed: float | None = Field(default=None, gt=0)
    speed_unit: str | None = Field(default=None, max_length=24)
    start_position: dict | None = None
    end_position: dict | None = None
    orientation: dict | None = None
    trigger_state: str | None = Field(default=None, pattern="^(ON|OFF|PULSE)$")
    trigger_start_ms: float | None = None
    trigger_end_ms: float | None = None
    remark: str | None = None


class TrajectoryPathSegmentRead(TrajectoryPathSegmentCreate, ResourceRead):
    pass


class PointContributionVersionCreate(BaseModel):
    program_version_id: str
    target_family: str = Field(
        pattern="^(ORANGE_PEEL|COLOR_DIFFERENCE|THICKNESS)$"
    )
    version: str = Field(min_length=1, max_length=32)
    method: str = Field(
        pattern="^(EXPERT|GEOMETRY|SIMULATION|DOE|FITTED_DEPOSITION)$"
    )
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    evidence_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class PointContributionVersionUpdate(BaseModel):
    program_version_id: str | None = None
    target_family: str | None = Field(
        default=None, pattern="^(ORANGE_PEEL|COLOR_DIFFERENCE|THICKNESS)$"
    )
    version: str | None = Field(default=None, min_length=1, max_length=32)
    method: str | None = Field(
        default=None, pattern="^(EXPERT|GEOMETRY|SIMULATION|DOE|FITTED_DEPOSITION)$"
    )
    status: str | None = Field(
        default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$"
    )
    evidence_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class PointContributionVersionRead(PointContributionVersionCreate, ResourceRead):
    approved_at: datetime | None


class PointContributionEntryCreate(BaseModel):
    contribution_version_id: str
    measurement_point_id: str
    brush_id: str | None = None
    path_segment_id: str | None = None
    overlap_ratio: float = Field(ge=0, le=1)
    contribution_weight: float = Field(gt=0, le=1)
    validation_score: float | None = Field(default=None, ge=0, le=1)
    evidence: dict | None = None


class PointContributionEntryUpdate(BaseModel):
    measurement_point_id: str | None = None
    brush_id: str | None = None
    path_segment_id: str | None = None
    overlap_ratio: float | None = Field(default=None, ge=0, le=1)
    contribution_weight: float | None = Field(default=None, gt=0, le=1)
    validation_score: float | None = Field(default=None, ge=0, le=1)
    evidence: dict | None = None


class PointContributionEntryRead(PointContributionEntryCreate, ResourceRead):
    source_key: str


class ProductionDeviceExecutionCreate(BaseModel):
    production_stage_run_id: str
    device_configuration_id: str
    trajectory_program_id: str
    executed_checksum: str = Field(min_length=1, max_length=128)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = Field(default="COMPLETED", max_length=24)
    source_system: str | None = Field(default=None, max_length=80)
    deviation_details: dict | None = None


class ProductionDeviceExecutionUpdate(BaseModel):
    device_configuration_id: str | None = None
    trajectory_program_id: str | None = None
    executed_checksum: str | None = Field(default=None, min_length=1, max_length=128)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str | None = Field(default=None, max_length=24)
    source_system: str | None = Field(default=None, max_length=80)
    deviation_details: dict | None = None


class ProductionDeviceExecutionRead(ProductionDeviceExecutionCreate, ResourceRead):
    pass


class PathSegmentExecutionCreate(BaseModel):
    path_segment_id: str
    actual_speed: float | None = Field(default=None, gt=0)
    speed_unit: str | None = Field(default=None, max_length=24)
    trigger_state: str | None = Field(default=None, pattern="^(ON|OFF|PULSE)$")
    actual_values: dict | None = None


class PathSegmentExecutionRead(PathSegmentExecutionCreate, ResourceRead):
    device_execution_id: str


class MaterialBatchCreate(BaseModel):
    batch_no: str = Field(min_length=1, max_length=64)
    material_code: str = Field(min_length=1, max_length=64)
    material_name: str = Field(min_length=1, max_length=120)
    material_type: str = Field(pattern="^(MIDCOAT|BASECOAT|CLEARCOAT)$")
    supplier: str | None = Field(default=None, max_length=120)
    viscosity: float | None = None
    solid_ratio: float | None = None
    coa_values: dict | None = None


class MaterialBatchRead(MaterialBatchCreate, ResourceRead):
    pass


class MaterialBatchUpdate(BaseModel):
    batch_no: str | None = Field(default=None, min_length=1, max_length=64)
    material_code: str | None = Field(default=None, min_length=1, max_length=64)
    material_name: str | None = Field(default=None, min_length=1, max_length=120)
    material_type: str | None = Field(default=None, pattern="^(MIDCOAT|BASECOAT|CLEARCOAT)$")
    supplier: str | None = Field(default=None, max_length=120)
    viscosity: float | None = None
    solid_ratio: float | None = None
    coa_values: dict | None = None


class ProductionRunCreate(BaseModel):
    run_no: str = Field(min_length=1, max_length=64)
    body_no: str | None = Field(default=None, max_length=64)
    factory_id: str
    vehicle_model_id: str
    color_id: str
    shift: str | None = Field(default=None, max_length=24)
    started_at: datetime
    completed_at: datetime | None = None
    context_values: dict | None = None


class ProductionRunRead(ProductionRunCreate, ResourceRead):
    pass


class ProductionRunUpdate(BaseModel):
    run_no: str | None = Field(default=None, min_length=1, max_length=64)
    body_no: str | None = Field(default=None, max_length=64)
    factory_id: str | None = None
    vehicle_model_id: str | None = None
    color_id: str | None = None
    shift: str | None = Field(default=None, max_length=24)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    context_values: dict | None = None


class ProductionStageRunCreate(BaseModel):
    process_stage: str
    program_version_id: str
    material_batch_id: str | None = None
    actual_parameters: dict | None = None
    status: str = Field(default="COMPLETED", max_length=24)


class ProductionStageRunRead(ProductionStageRunCreate, ResourceRead):
    production_run_id: str


class ProductionStageRunUpdate(BaseModel):
    process_stage: str | None = None
    program_version_id: str | None = None
    material_batch_id: str | None = None
    actual_parameters: dict | None = None
    status: str | None = Field(default=None, max_length=24)


class ActualParameterCreate(BaseModel):
    brush_id: str | None = None
    parameter_definition_id: str | None = None
    parameter_code: str = Field(min_length=1, max_length=64)
    actual_value: float
    unit: str = Field(max_length=24)
    sampled_at: datetime
    source_system: str | None = Field(default=None, max_length=64)


class ActualParameterRead(ActualParameterCreate, ResourceRead):
    production_stage_run_id: str


class ActualParameterUpdate(BaseModel):
    brush_id: str | None = None
    parameter_definition_id: str | None = None
    parameter_code: str | None = Field(default=None, min_length=1, max_length=64)
    actual_value: float | None = None
    unit: str | None = Field(default=None, max_length=24)
    sampled_at: datetime | None = None
    source_system: str | None = Field(default=None, max_length=64)


class SprayProgramVersionRead(ResourceRead):
    spray_program_id: str
    version: str
    status: str
    source_type: str
    is_master_sample: bool
    approved_by: str | None
    approved_at: datetime | None
    effective_from: datetime | None

    model_config = ConfigDict(from_attributes=True)
