from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResourceRead(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VehicleModelCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    remark: str | None = None


class VehicleModelUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    remark: str | None = None


class VehicleModelRead(VehicleModelCreate, ResourceRead):
    pass


class ColorCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    color_type: str = Field(pattern="^(MIDCOAT|BASECOAT)$")
    feature_values: dict | None = None
    supplier: str | None = Field(default=None, max_length=120)
    tds_uri: str | None = Field(default=None, max_length=500)
    msds_uri: str | None = Field(default=None, max_length=500)
    coa_uri: str | None = Field(default=None, max_length=500)
    doe_uri: str | None = Field(default=None, max_length=500)
    digital_standard: dict | None = None
    remark: str | None = None


class ColorUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    color_type: str | None = Field(default=None, pattern="^(MIDCOAT|BASECOAT)$")
    feature_values: dict | None = None
    supplier: str | None = Field(default=None, max_length=120)
    tds_uri: str | None = Field(default=None, max_length=500)
    msds_uri: str | None = Field(default=None, max_length=500)
    coa_uri: str | None = Field(default=None, max_length=500)
    doe_uri: str | None = Field(default=None, max_length=500)
    digital_standard: dict | None = None
    remark: str | None = None


class ColorRead(ColorCreate, ResourceRead):
    pass


class PartCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    material: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class PartUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    material: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class PartRead(PartCreate, ResourceRead):
    pass


class FactoryVehicleModelCreate(BaseModel):
    factory_id: str
    vehicle_model_id: str
    is_active: bool = True


class FactoryVehicleModelRead(FactoryVehicleModelCreate, ResourceRead):
    pass


class VehicleModelColorCreate(BaseModel):
    vehicle_model_id: str
    color_id: str
    is_active: bool = True


class VehicleModelColorRead(VehicleModelColorCreate, ResourceRead):
    pass


class MeasurementGroupCreate(BaseModel):
    code: str = Field(min_length=1, max_length=48)
    name: str = Field(min_length=1, max_length=120)
    vehicle_model_id: str
    quality_type: str
    expected_point_count: int | None = Field(default=None, ge=0)
    remark: str | None = None


class MeasurementGroupUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=48)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    vehicle_model_id: str | None = None
    quality_type: str | None = None
    expected_point_count: int | None = Field(default=None, ge=0)
    remark: str | None = None


class MeasurementGroupRead(MeasurementGroupCreate, ResourceRead):
    pass


class MeasurementPointCreate(BaseModel):
    code: str = Field(min_length=1, max_length=48)
    name: str = Field(min_length=1, max_length=120)
    vehicle_model_id: str
    part_id: str
    point_type: str = Field(default="QUALITY", max_length=32)
    region: str | None = Field(default=None, max_length=80)
    quality_types: list[str] = Field(default_factory=list)
    is_match_point: bool = False


class MeasurementPointUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=48)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    vehicle_model_id: str | None = None
    part_id: str | None = None
    point_type: str | None = Field(default=None, max_length=32)
    region: str | None = Field(default=None, max_length=80)
    quality_types: list[str] | None = None
    is_match_point: bool | None = None


class MeasurementPointRead(MeasurementPointCreate, ResourceRead):
    pass


class MeasurementGroupPointCreate(BaseModel):
    measurement_point_id: str
    sequence_no: int = Field(default=0, ge=0)


class MeasurementGroupPointBind(MeasurementGroupPointCreate):
    measurement_group_id: str


class MeasurementGroupPointRead(MeasurementGroupPointCreate, ResourceRead):
    measurement_group_id: str


class MasterDataSummary(BaseModel):
    factories: int
    vehicle_models: int
    colors: int
    parts: int
    measurement_groups: int
    measurement_points: int
    approved_point_contributions: int
