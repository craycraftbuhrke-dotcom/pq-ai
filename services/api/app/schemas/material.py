from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.master_data import ResourceRead


class MaterialCharacteristicDefinitionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(
        pattern="^(VISCOSITY_RHEOLOGY|SOLIDS|DENSITY|PIGMENT_EFFECT|LEVELING_SURFACE)$"
    )
    canonical_unit: str = Field(min_length=1, max_length=24)
    target_families: list[str] = Field(min_length=1)
    is_model_feature: bool = True
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|RETIRED)$")
    description: str | None = None


class MaterialCharacteristicDefinitionUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(
        default=None,
        pattern="^(VISCOSITY_RHEOLOGY|SOLIDS|DENSITY|PIGMENT_EFFECT|LEVELING_SURFACE)$",
    )
    canonical_unit: str | None = Field(default=None, min_length=1, max_length=24)
    target_families: list[str] | None = Field(default=None, min_length=1)
    is_model_feature: bool | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|RETIRED)$")
    description: str | None = None


class MaterialCharacteristicDefinitionRead(
    MaterialCharacteristicDefinitionCreate, ResourceRead
):
    pass


class MaterialTestMethodCreate(BaseModel):
    characteristic_definition_id: str
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=32)
    method_type: str = Field(min_length=1, max_length=64)
    result_unit: str = Field(min_length=1, max_length=24)
    procedure_uri: str | None = Field(default=None, max_length=500)
    conditions: dict | None = None
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|RETIRED)$")
    remark: str | None = None


class MaterialTestMethodUpdate(BaseModel):
    characteristic_definition_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    method_type: str | None = Field(default=None, min_length=1, max_length=64)
    result_unit: str | None = Field(default=None, min_length=1, max_length=24)
    procedure_uri: str | None = Field(default=None, max_length=500)
    conditions: dict | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|RETIRED)$")
    remark: str | None = None


class MaterialTestMethodRead(MaterialTestMethodCreate, ResourceRead):
    pass


class MaterialSpecificationCreate(BaseModel):
    material_code: str = Field(min_length=1, max_length=64)
    characteristic_definition_id: str
    method_id: str
    version: str = Field(min_length=1, max_length=32)
    lower_limit: float | None = None
    upper_limit: float | None = None
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class MaterialSpecificationUpdate(BaseModel):
    material_code: str | None = Field(default=None, min_length=1, max_length=64)
    characteristic_definition_id: str | None = None
    method_id: str | None = None
    version: str | None = Field(default=None, min_length=1, max_length=32)
    lower_limit: float | None = None
    upper_limit: float | None = None
    status: str | None = Field(
        default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$"
    )
    source_uri: str | None = Field(default=None, max_length=500)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class MaterialSpecificationRead(MaterialSpecificationCreate, ResourceRead):
    approved_at: datetime | None


class MaterialCharacteristicApplicabilityCreate(BaseModel):
    characteristic_definition_id: str
    material_type: str = Field(pattern="^(MIDCOAT|BASECOAT|CLEARCOAT)$")
    process_stage: str
    target_family: str
    is_required: bool = False
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class MaterialCharacteristicApplicabilityUpdate(BaseModel):
    characteristic_definition_id: str | None = None
    material_type: str | None = Field(
        default=None, pattern="^(MIDCOAT|BASECOAT|CLEARCOAT)$"
    )
    process_stage: str | None = None
    target_family: str | None = None
    is_required: bool | None = None
    status: str | None = Field(
        default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$"
    )
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class MaterialCharacteristicApplicabilityRead(
    MaterialCharacteristicApplicabilityCreate, ResourceRead
):
    approved_at: datetime | None


class MaterialBatchTestResultCreate(BaseModel):
    result_no: str = Field(min_length=1, max_length=80)
    material_batch_id: str
    characteristic_definition_id: str
    method_id: str
    result_value: float
    unit: str = Field(min_length=1, max_length=24)
    tested_at: datetime
    tested_by: str | None = Field(default=None, max_length=80)
    source_uri: str | None = Field(default=None, max_length=500)
    raw_values: dict | None = None
    remark: str | None = None


class MaterialBatchTestResultUpdate(BaseModel):
    result_no: str | None = Field(default=None, min_length=1, max_length=80)
    material_batch_id: str | None = None
    characteristic_definition_id: str | None = None
    method_id: str | None = None
    result_value: float | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    tested_at: datetime | None = None
    tested_by: str | None = Field(default=None, max_length=80)
    source_uri: str | None = Field(default=None, max_length=500)
    raw_values: dict | None = None
    remark: str | None = None


class MaterialBatchTestResultRead(MaterialBatchTestResultCreate, ResourceRead):
    specification_id: str | None
    reliability_status: str
    reliability_issues: list[str] | None
    is_within_spec: bool | None
