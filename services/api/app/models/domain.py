from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProcessStage(StrEnum):
    MIDCOAT_EXT = "MIDCOAT_EXT"
    BASECOAT_1 = "BASECOAT_1"
    BASECOAT_2 = "BASECOAT_2"
    CLEARCOAT_1 = "CLEARCOAT_1"
    CLEARCOAT_2 = "CLEARCOAT_2"


class QualityType(StrEnum):
    ORANGE_PEEL = "ORANGE_PEEL"
    COLOR_DIFFERENCE = "COLOR_DIFFERENCE"
    THICKNESS = "THICKNESS"


class VersionStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class RecommendationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"


class AppUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_user"

    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), unique=True)
    department: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permission"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("role.id"), nullable=False)


class RolePermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role_id: Mapped[str] = mapped_column(ForeignKey("role.id"), nullable=False)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permission.id"), nullable=False)


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_key"
    __table_args__ = (Index("ix_api_key_prefix", "key_prefix"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_actor_time", "actor_user_id", "occurred_at"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
    )

    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("app_user.id"))
    actor_username: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    http_method: Mapped[str] = mapped_column(String(12), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    status_code: Mapped[int] = mapped_column(nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class Factory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "factory"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    site_owner: Mapped[str | None] = mapped_column(String(80))
    remark: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class VehicleModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_model"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class FactoryVehicleModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "factory_vehicle_model"
    __table_args__ = (
        UniqueConstraint("factory_id", "vehicle_model_id", name="uq_factory_vehicle_model"),
    )

    factory_id: Mapped[str] = mapped_column(ForeignKey("factory.id"), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(ForeignKey("vehicle_model.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Color(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "color"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    color_type: Mapped[str] = mapped_column(String(24), nullable=False)
    feature_values: Mapped[dict | None] = mapped_column(JSON)
    supplier: Mapped[str | None] = mapped_column(String(120))
    tds_uri: Mapped[str | None] = mapped_column(String(500))
    msds_uri: Mapped[str | None] = mapped_column(String(500))
    coa_uri: Mapped[str | None] = mapped_column(String(500))
    doe_uri: Mapped[str | None] = mapped_column(String(500))
    digital_standard: Mapped[dict | None] = mapped_column(JSON)
    remark: Mapped[str | None] = mapped_column(Text)


class VehicleModelColor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_model_color"
    __table_args__ = (
        UniqueConstraint("vehicle_model_id", "color_id", name="uq_vehicle_model_color"),
    )

    vehicle_model_id: Mapped[str] = mapped_column(ForeignKey("vehicle_model.id"), nullable=False)
    color_id: Mapped[str] = mapped_column(ForeignKey("color.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Part(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "part"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    material: Mapped[str | None] = mapped_column(String(80))
    region: Mapped[str | None] = mapped_column(String(80))
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementPoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_point"
    __table_args__ = (UniqueConstraint("vehicle_model_id", "code", name="uq_point_model_code"),)

    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(ForeignKey("vehicle_model.id"), nullable=False)
    part_id: Mapped[str] = mapped_column(ForeignKey("part.id"), nullable=False)
    point_type: Mapped[str] = mapped_column(String(32), default="QUALITY", nullable=False)
    region: Mapped[str | None] = mapped_column(String(80))
    quality_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_match_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MeasurementGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_group"
    __table_args__ = (
        UniqueConstraint("vehicle_model_id", "code", name="uq_group_model_code"),
    )

    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(ForeignKey("vehicle_model.id"), nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_point_count: Mapped[int | None] = mapped_column()
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementGroupPoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_group_point"
    __table_args__ = (
        UniqueConstraint("measurement_group_id", "measurement_point_id", name="uq_group_point"),
    )

    measurement_group_id: Mapped[str] = mapped_column(
        ForeignKey("measurement_group.id"), nullable=False
    )
    measurement_point_id: Mapped[str] = mapped_column(
        ForeignKey("measurement_point.id"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(default=0, nullable=False)


class SprayProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spray_program"
    __table_args__ = (
        UniqueConstraint("factory_id", "program_code", name="uq_factory_program_code"),
    )

    program_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    factory_id: Mapped[str] = mapped_column(ForeignKey("factory.id"), nullable=False)
    process_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    station_code: Mapped[str] = mapped_column(String(32), nullable=False)
    station_name: Mapped[str] = mapped_column(String(120), nullable=False)
    robot_model: Mapped[str | None] = mapped_column(String(120))
    remark: Mapped[str | None] = mapped_column(Text)


class SprayProgramVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spray_program_version"
    __table_args__ = (
        UniqueConstraint("spray_program_id", "version", name="uq_program_version"),
    )

    spray_program_id: Mapped[str] = mapped_column(ForeignKey("spray_program.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default=VersionStatus.DRAFT, nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), default="MANUAL", nullable=False)
    is_master_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProgramVehicleModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_vehicle_model"
    __table_args__ = (
        UniqueConstraint("program_version_id", "vehicle_model_id", name="uq_program_model"),
    )

    program_version_id: Mapped[str] = mapped_column(
        ForeignKey("spray_program_version.id"), nullable=False
    )
    vehicle_model_id: Mapped[str] = mapped_column(ForeignKey("vehicle_model.id"), nullable=False)


class ProgramColor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_color"
    __table_args__ = (
        UniqueConstraint("program_version_id", "color_id", name="uq_program_color"),
    )

    program_version_id: Mapped[str] = mapped_column(
        ForeignKey("spray_program_version.id"), nullable=False
    )
    color_id: Mapped[str] = mapped_column(ForeignKey("color.id"), nullable=False)


class ParameterDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parameter_definition"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    aggregation_method: Mapped[str] = mapped_column(
        String(32), default="WEIGHTED_AVERAGE", nullable=False
    )
    hard_min: Mapped[float | None] = mapped_column(Float)
    hard_max: Mapped[float | None] = mapped_column(Float)
    is_recommendable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Brush(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brush"
    __table_args__ = (
        UniqueConstraint("program_version_id", "brush_no", name="uq_program_brush_no"),
    )

    program_version_id: Mapped[str] = mapped_column(
        ForeignKey("spray_program_version.id"), nullable=False
    )
    brush_no: Mapped[str] = mapped_column(String(32), nullable=False)
    brush_table_no: Mapped[str] = mapped_column(String(64), nullable=False)
    spray_position: Mapped[str | None] = mapped_column(String(120))
    part_id: Mapped[str | None] = mapped_column(ForeignKey("part.id"))
    remark: Mapped[str | None] = mapped_column(Text)


class BrushParameter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brush_parameter"
    __table_args__ = (
        UniqueConstraint("brush_id", "parameter_code", name="uq_brush_parameter"),
    )

    brush_id: Mapped[str] = mapped_column(ForeignKey("brush.id"), nullable=False)
    parameter_definition_id: Mapped[str | None] = mapped_column(
        ForeignKey("parameter_definition.id")
    )
    parameter_code: Mapped[str] = mapped_column(String(64), nullable=False)
    parameter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    configured_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    soft_min: Mapped[float | None] = mapped_column(Float)
    soft_max: Mapped[float | None] = mapped_column(Float)
    hard_min: Mapped[float | None] = mapped_column(Float)
    hard_max: Mapped[float | None] = mapped_column(Float)
    is_recommendable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BrushPointContribution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brush_point_contribution"
    __table_args__ = (
        UniqueConstraint("brush_id", "measurement_point_id", name="uq_brush_point"),
    )

    brush_id: Mapped[str] = mapped_column(ForeignKey("brush.id"), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(
        ForeignKey("measurement_point.id"), nullable=False
    )
    overlap_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="EXPERT", nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MaterialBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_batch"

    batch_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    material_code: Mapped[str] = mapped_column(String(64), nullable=False)
    material_name: Mapped[str] = mapped_column(String(120), nullable=False)
    material_type: Mapped[str] = mapped_column(String(24), nullable=False)
    supplier: Mapped[str | None] = mapped_column(String(120))
    viscosity: Mapped[float | None] = mapped_column(Float)
    solid_ratio: Mapped[float | None] = mapped_column(Float)
    coa_values: Mapped[dict | None] = mapped_column(JSON)


class ProductionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_run"
    __table_args__ = (
        Index("ix_production_run_context", "factory_id", "vehicle_model_id", "color_id"),
    )

    run_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    body_no: Mapped[str | None] = mapped_column(String(64), index=True)
    factory_id: Mapped[str] = mapped_column(ForeignKey("factory.id"), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(ForeignKey("vehicle_model.id"), nullable=False)
    color_id: Mapped[str] = mapped_column(ForeignKey("color.id"), nullable=False)
    shift: Mapped[str | None] = mapped_column(String(24))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context_values: Mapped[dict | None] = mapped_column(JSON)


class ProductionStageRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_stage_run"
    __table_args__ = (
        UniqueConstraint("production_run_id", "process_stage", name="uq_run_stage"),
    )

    production_run_id: Mapped[str] = mapped_column(ForeignKey("production_run.id"), nullable=False)
    process_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    program_version_id: Mapped[str] = mapped_column(
        ForeignKey("spray_program_version.id"), nullable=False
    )
    material_batch_id: Mapped[str | None] = mapped_column(ForeignKey("material_batch.id"))
    actual_parameters: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="COMPLETED", nullable=False)


class ActualParameter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actual_parameter"
    __table_args__ = (
        Index("ix_actual_parameter_stage_code", "production_stage_run_id", "parameter_code"),
    )

    production_stage_run_id: Mapped[str] = mapped_column(
        ForeignKey("production_stage_run.id"), nullable=False
    )
    brush_id: Mapped[str | None] = mapped_column(ForeignKey("brush.id"))
    parameter_definition_id: Mapped[str | None] = mapped_column(
        ForeignKey("parameter_definition.id")
    )
    parameter_code: Mapped[str] = mapped_column(String(64), nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(64))


class QualityMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_measurement"
    __table_args__ = (
        Index("ix_quality_point_time", "measurement_point_id", "measured_at"),
    )

    data_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    production_run_id: Mapped[str] = mapped_column(ForeignKey("production_run.id"), nullable=False)
    measurement_group_id: Mapped[str | None] = mapped_column(ForeignKey("measurement_group.id"))
    measurement_point_id: Mapped[str] = mapped_column(
        ForeignKey("measurement_point.id"), nullable=False
    )
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    data_type: Mapped[str] = mapped_column(String(24), default="TEST", nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    measured_by: Mapped[str | None] = mapped_column(String(80))
    device_code: Mapped[str | None] = mapped_column(String(64))
    status_score: Mapped[float | None] = mapped_column(Float)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class QualityMetricDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_metric_definition"
    __table_args__ = (
        UniqueConstraint("quality_type", "code", name="uq_quality_type_metric_code"),
    )

    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(24))
    display_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class QualityMetricValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_metric_value"
    __table_args__ = (
        UniqueConstraint("measurement_id", "metric_code", name="uq_measurement_metric"),
    )

    measurement_id: Mapped[str] = mapped_column(
        ForeignKey("quality_measurement.id"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    corrected_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(24))


class QualityStandard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_standard"
    __table_args__ = (
        Index("ix_standard_match", "quality_type", "metric_code", "vehicle_model_id", "color_id"),
    )

    standard_no: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    standard_type: Mapped[str] = mapped_column(String(24), default="PRODUCTION", nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    vehicle_model_id: Mapped[str | None] = mapped_column(ForeignKey("vehicle_model.id"))
    color_id: Mapped[str | None] = mapped_column(ForeignKey("color.id"))
    part_id: Mapped[str | None] = mapped_column(ForeignKey("part.id"))
    measurement_point_id: Mapped[str | None] = mapped_column(ForeignKey("measurement_point.id"))
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(24))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PointFeatureSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "point_feature_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "production_run_id",
            "measurement_point_id",
            "feature_set_version",
            name="uq_run_point_feature_version",
        ),
    )

    production_run_id: Mapped[str] = mapped_column(ForeignKey("production_run.id"), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(
        ForeignKey("measurement_point.id"), nullable=False
    )
    feature_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_version"
    __table_args__ = (
        UniqueConstraint("model_code", "version", name="uq_model_version"),
    )

    model_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    model_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    evaluation_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    training_sample_count: Mapped[int] = mapped_column(default=0, nullable=False)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default=VersionStatus.DRAFT, nullable=False)


class PredictionResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prediction_result"
    __table_args__ = (
        Index("ix_prediction_run_point", "production_run_id", "measurement_point_id"),
    )

    model_version_id: Mapped[str] = mapped_column(ForeignKey("model_version.id"), nullable=False)
    production_run_id: Mapped[str] = mapped_column(ForeignKey("production_run.id"), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(
        ForeignKey("measurement_point.id"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float | None] = mapped_column(Float)
    upper_bound: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DiagnosisResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diagnosis_result"

    prediction_result_id: Mapped[str | None] = mapped_column(ForeignKey("prediction_result.id"))
    production_run_id: Mapped[str] = mapped_column(ForeignKey("production_run.id"), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(
        ForeignKey("measurement_point.id"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    factor_contributions: Mapped[list] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    causality_status: Mapped[str] = mapped_column(
        String(24), default="CORRELATION_ONLY", nullable=False
    )


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation"
    __table_args__ = (Index("ix_recommendation_status", "status", "created_at"),)

    recommendation_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    production_run_id: Mapped[str] = mapped_column(ForeignKey("production_run.id"), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(
        ForeignKey("measurement_point.id"), nullable=False
    )
    target_quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    diagnosis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=RecommendationStatus.PENDING, nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    constraints_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_by: Mapped[str | None] = mapped_column(String(80))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecommendationAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_action"

    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendation.id"), nullable=False)
    process_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    brush_no: Mapped[str | None] = mapped_column(String(32))
    parameter_code: Mapped[str] = mapped_column(String(64), nullable=False)
    parameter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_value: Mapped[float] = mapped_column(Float, nullable=False)
    executed_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    hard_min: Mapped[float | None] = mapped_column(Float)
    hard_max: Mapped[float | None] = mapped_column(Float)


class ClosedLoopEvaluation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "closed_loop_evaluation"
    __table_args__ = (
        UniqueConstraint("recommendation_id", name="uq_recommendation_evaluation"),
    )

    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendation.id"), nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    verified_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    is_effective: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by: Mapped[str] = mapped_column(String(80), nullable=False)
    conclusion: Mapped[str | None] = mapped_column(Text)


class IntegrationEndpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_endpoint"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    system_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(24), default="INBOUND", nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500))
    auth_type: Mapped[str] = mapped_column(String(32), default="API_KEY", nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntegrationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_event"
    __table_args__ = (
        UniqueConstraint("endpoint_id", "source_event_id", name="uq_endpoint_source_event"),
        Index("ix_integration_event_status_time", "status", "created_at"),
    )

    event_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    endpoint_id: Mapped[str] = mapped_column(ForeignKey("integration_endpoint.id"), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(24), default="INBOUND", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    mapped_payload: Mapped[dict | None] = mapped_column(JSON)
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=3, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
