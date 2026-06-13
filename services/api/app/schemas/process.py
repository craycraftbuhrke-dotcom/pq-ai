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
