from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
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
    password_hash: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_role"

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
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uk_user_role"),)

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), nullable=False)


class RolePermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uk_role_permission"),
    )

    role_id: Mapped[str] = mapped_column(String(36), nullable=False)
    permission_id: Mapped[str] = mapped_column(String(36), nullable=False)


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_key"
    __table_args__ = (Index("ix_api_key_prefix", "key_prefix"),)

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
    actor_user_id: Mapped[str | None] = mapped_column(String(36))
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
        UniqueConstraint("factory_id", "vehicle_model_id", name="uk_factory_vehicle_model"),
    )

    factory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
        UniqueConstraint("vehicle_model_id", "color_id", name="uk_vehicle_model_color"),
    )

    vehicle_model_id: Mapped[str] = mapped_column(String(36), nullable=False)
    color_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
    __table_args__ = (UniqueConstraint("vehicle_model_id", "code", name="uk_point_model_code"),)

    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(String(36), nullable=False)
    part_id: Mapped[str] = mapped_column(String(36), nullable=False)
    point_type: Mapped[str] = mapped_column(String(32), default="QUALITY", nullable=False)
    region: Mapped[str | None] = mapped_column(String(80))
    quality_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_match_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MeasurementGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_group"
    __table_args__ = (
        UniqueConstraint("vehicle_model_id", "code", name="uk_group_model_code"),
    )

    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_point_count: Mapped[int | None] = mapped_column()
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementGroupPoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_group_point"
    __table_args__ = (
        UniqueConstraint("measurement_group_id", "measurement_point_id", name="uk_group_point"),
    )

    measurement_group_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(default=0, nullable=False)


class SprayProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spray_program"
    __table_args__ = (
        UniqueConstraint("factory_id", "program_code", name="uk_factory_program_code"),
    )

    program_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    factory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    process_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    station_code: Mapped[str] = mapped_column(String(32), nullable=False)
    station_name: Mapped[str] = mapped_column(String(120), nullable=False)
    robot_model: Mapped[str | None] = mapped_column(String(120))
    remark: Mapped[str | None] = mapped_column(Text)


class SprayProgramVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spray_program_version"
    __table_args__ = (
        UniqueConstraint("spray_program_id", "version", name="uk_program_version"),
    )

    spray_program_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default=VersionStatus.DRAFT, nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), default="MANUAL", nullable=False)
    is_master_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProgramVehicleModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_vehicle_model"
    __table_args__ = (
        UniqueConstraint("program_version_id", "vehicle_model_id", name="uk_program_model"),
    )

    program_version_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    vehicle_model_id: Mapped[str] = mapped_column(String(36), nullable=False)


class ProgramColor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_color"
    __table_args__ = (
        UniqueConstraint("program_version_id", "color_id", name="uk_program_color"),
    )

    program_version_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    color_id: Mapped[str] = mapped_column(String(36), nullable=False)


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
        UniqueConstraint("program_version_id", "brush_no", name="uk_program_brush_no"),
    )

    program_version_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    brush_no: Mapped[str] = mapped_column(String(32), nullable=False)
    brush_table_no: Mapped[str] = mapped_column(String(64), nullable=False)
    spray_position: Mapped[str | None] = mapped_column(String(120))
    part_id: Mapped[str | None] = mapped_column(String(36))
    remark: Mapped[str | None] = mapped_column(Text)


class BrushParameter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brush_parameter"
    __table_args__ = (
        UniqueConstraint("brush_id", "parameter_code", name="uk_brush_parameter"),
    )

    brush_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parameter_definition_id: Mapped[str | None] = mapped_column(String(36))
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
        UniqueConstraint("brush_id", "measurement_point_id", name="uk_brush_point"),
    )

    brush_id: Mapped[str] = mapped_column(String(36), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    overlap_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="EXPERT", nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", default="1.0", nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DurrRobot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "durr_robot"
    __table_args__ = (UniqueConstraint("factory_id", "code", name="uk_factory_durr_robot"),)

    factory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    controller_software_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)


class DurrApplicationController(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "durr_application_controller"
    __table_args__ = (
        UniqueConstraint("factory_id", "code", name="uk_factory_durr_controller"),
    )

    factory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    software_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)


class DurrRotaryAtomizer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "durr_rotary_atomizer"
    __table_args__ = (
        UniqueConstraint("factory_id", "code", name="uk_factory_durr_atomizer"),
    )

    factory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    controller_id: Mapped[str | None] = mapped_column(String(36))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    bell_cup_type: Mapped[str | None] = mapped_column(String(120))
    bell_cup_code: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)


class ProgramDeviceConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_device_configuration"
    __table_args__ = (
        UniqueConstraint(
            "program_version_id",
            "configuration_version",
            name="uk_program_device_configuration_version",
        ),
    )

    program_version_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    robot_id: Mapped[str] = mapped_column(String(36), nullable=False)
    atomizer_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    controller_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    configuration_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class TrajectoryProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trajectory_program"
    __table_args__ = (
        UniqueConstraint(
            "program_version_id",
            "trajectory_code",
            "version",
            name="uk_program_trajectory_version",
        ),
    )

    program_version_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    trajectory_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    coordinate_system: Mapped[str | None] = mapped_column(String(80))
    tcp_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class TrajectoryPathSegment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trajectory_path_segment"
    __table_args__ = (
        UniqueConstraint(
            "trajectory_program_id",
            "segment_no",
            name="uk_trajectory_path_segment_no",
        ),
    )

    trajectory_program_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    segment_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    brush_id: Mapped[str | None] = mapped_column(String(36))
    part_id: Mapped[str | None] = mapped_column(String(36))
    tcp_name: Mapped[str | None] = mapped_column(String(120))
    configured_speed: Mapped[float | None] = mapped_column(Float)
    speed_unit: Mapped[str | None] = mapped_column(String(24))
    start_position: Mapped[dict | None] = mapped_column(JSON)
    end_position: Mapped[dict | None] = mapped_column(JSON)
    orientation: Mapped[dict | None] = mapped_column(JSON)
    trigger_state: Mapped[str] = mapped_column(String(24), default="ON", nullable=False)
    trigger_start_ms: Mapped[float | None] = mapped_column(Float)
    trigger_end_ms: Mapped[float | None] = mapped_column(Float)
    remark: Mapped[str | None] = mapped_column(Text)


class PointContributionVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "point_contribution_version"
    __table_args__ = (
        UniqueConstraint(
            "program_version_id",
            "target_family",
            "version",
            name="uk_program_target_contribution_version",
        ),
    )

    program_version_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    target_family: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    evidence_uri: Mapped[str | None] = mapped_column(String(500))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class PointContributionEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "point_contribution_entry"
    __table_args__ = (
        UniqueConstraint(
            "contribution_version_id",
            "measurement_point_id",
            "source_key",
            name="uk_version_point_contribution_source",
        ),
    )

    contribution_version_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    brush_id: Mapped[str | None] = mapped_column(String(36))
    path_segment_id: Mapped[str | None] = mapped_column(String(36))
    source_key: Mapped[str] = mapped_column(String(100), nullable=False)
    overlap_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False)
    validation_score: Mapped[float | None] = mapped_column(Float)
    evidence: Mapped[dict | None] = mapped_column(JSON)


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


class MaterialCharacteristicDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_characteristic_definition"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    target_families: Mapped[list] = mapped_column(JSON, nullable=False)
    is_model_feature: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class MaterialTestMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_test_method"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uk_material_test_method_version"),
    )

    characteristic_definition_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    method_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    procedure_uri: Mapped[str | None] = mapped_column(String(500))
    conditions: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class MaterialSpecification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_specification"
    __table_args__ = (
        UniqueConstraint(
            "material_code",
            "characteristic_definition_id",
            "method_id",
            "version",
            name="uk_material_specification_version",
        ),
    )

    material_code: Mapped[str] = mapped_column(String(64), nullable=False)
    characteristic_definition_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    method_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    lower_limit: Mapped[float | None] = mapped_column(Float)
    upper_limit: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class MaterialCharacteristicApplicability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_characteristic_applicability"
    __table_args__ = (
        UniqueConstraint(
            "characteristic_definition_id",
            "material_type",
            "process_stage",
            "target_family",
            name="uk_material_characteristic_applicability",
        ),
    )

    characteristic_definition_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    material_type: Mapped[str] = mapped_column(String(24), nullable=False)
    process_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    target_family: Mapped[str] = mapped_column(String(32), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class MaterialBatchTestResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_batch_test_result"
    __table_args__ = (
        Index(
            "ix_material_result_batch_characteristic_time",
            "material_batch_id",
            "characteristic_definition_id",
            "tested_at",
        ),
    )

    result_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    material_batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    characteristic_definition_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    method_id: Mapped[str] = mapped_column(String(36), nullable=False)
    specification_id: Mapped[str | None] = mapped_column(String(36))
    result_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tested_by: Mapped[str | None] = mapped_column(String(80))
    source_uri: Mapped[str | None] = mapped_column(String(500))
    raw_values: Mapped[dict | None] = mapped_column(JSON)
    reliability_status: Mapped[str] = mapped_column(
        String(24), default="UNVERIFIED", nullable=False
    )
    reliability_issues: Mapped[list | None] = mapped_column(JSON)
    is_within_spec: Mapped[bool | None] = mapped_column(Boolean)
    remark: Mapped[str | None] = mapped_column(Text)


class ProductionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_run"
    __table_args__ = (
        Index("ix_production_run_context", "factory_id", "vehicle_model_id", "color_id"),
    )

    run_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    body_no: Mapped[str | None] = mapped_column(String(64), index=True)
    factory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(String(36), nullable=False)
    color_id: Mapped[str] = mapped_column(String(36), nullable=False)
    shift: Mapped[str | None] = mapped_column(String(24))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context_values: Mapped[dict | None] = mapped_column(JSON)


class ProductionStageRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_stage_run"
    __table_args__ = (
        UniqueConstraint("production_run_id", "process_stage", name="uk_run_stage"),
    )

    production_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    process_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    program_version_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    material_batch_id: Mapped[str | None] = mapped_column(String(36))
    actual_parameters: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="COMPLETED", nullable=False)


class ProductionDeviceExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_device_execution"
    __table_args__ = (
        UniqueConstraint("production_stage_run_id", name="uk_stage_device_execution"),
    )

    production_stage_run_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    device_configuration_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    trajectory_program_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    executed_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="COMPLETED", nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(80))
    deviation_details: Mapped[dict | None] = mapped_column(JSON)


class PathSegmentExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "path_segment_execution"
    __table_args__ = (
        UniqueConstraint(
            "device_execution_id",
            "path_segment_id",
            name="uk_device_path_segment_execution",
        ),
    )

    device_execution_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    path_segment_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    actual_speed: Mapped[float | None] = mapped_column(Float)
    speed_unit: Mapped[str | None] = mapped_column(String(24))
    trigger_state: Mapped[str | None] = mapped_column(String(24))
    actual_values: Mapped[dict | None] = mapped_column(JSON)


class ActualParameter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actual_parameter"
    __table_args__ = (
        Index("ix_actual_parameter_stage_code", "production_stage_run_id", "parameter_code"),
    )

    production_stage_run_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    brush_id: Mapped[str | None] = mapped_column(String(36))
    parameter_definition_id: Mapped[str | None] = mapped_column(String(36))
    parameter_code: Mapped[str] = mapped_column(String(64), nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(64))


class MeasurementInstrument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_instrument"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(32), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    firmware_version: Mapped[str | None] = mapped_column(String(64))
    supported_quality_types: Mapped[list] = mapped_column(JSON, nullable=False)
    calibration_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_method"
    __table_args__ = (UniqueConstraint("code", "version", name="uk_measurement_method_version"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(32), nullable=False)
    method_type: Mapped[str] = mapped_column(String(64), nullable=False)
    probe_code: Mapped[str | None] = mapped_column(String(64))
    substrate_type: Mapped[str | None] = mapped_column(String(80))
    geometry_class: Mapped[str | None] = mapped_column(String(80))
    layer_scope: Mapped[str | None] = mapped_column(String(80))
    requires_reference: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_direction: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    minimum_repeats: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)


class MeasurementReferenceStandard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_reference_standard"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    serial_no: Mapped[str | None] = mapped_column(String(120))
    certificate_no: Mapped[str | None] = mapped_column(String(120))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reference_values: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementImportProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_import_profile"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uk_measurement_import_profile_version"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    field_mapping: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementCalibrationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_calibration_record"
    __table_args__ = (Index("ix_calibration_instrument_time", "instrument_id", "calibrated_at"),)

    calibration_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    method_id: Mapped[str | None] = mapped_column(String(36))
    reference_standard_id: Mapped[str | None] = mapped_column(String(36))
    calibrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String(24), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(80), nullable=False)
    certificate_uri: Mapped[str | None] = mapped_column(String(500))
    check_values: Mapped[dict | None] = mapped_column(JSON)
    remark: Mapped[str | None] = mapped_column(Text)


class QualityMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_measurement"
    __table_args__ = (
        Index("ix_quality_point_time", "measurement_point_id", "measured_at"),
    )

    data_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    production_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    measurement_group_id: Mapped[str | None] = mapped_column(String(36))
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    data_type: Mapped[str] = mapped_column(String(24), default="TEST", nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    measured_by: Mapped[str | None] = mapped_column(String(80))
    device_code: Mapped[str | None] = mapped_column(String(64))
    instrument_id: Mapped[str | None] = mapped_column(String(36))
    measurement_method_id: Mapped[str | None] = mapped_column(String(36))
    calibration_record_id: Mapped[str | None] = mapped_column(String(36))
    reference_standard_id: Mapped[str | None] = mapped_column(String(36))
    import_profile_id: Mapped[str | None] = mapped_column(String(36))
    measurement_direction: Mapped[str | None] = mapped_column(String(32))
    raw_file_uri: Mapped[str | None] = mapped_column(String(500))
    reliability_status: Mapped[str] = mapped_column(
        String(24), default="UNVERIFIED", nullable=False
    )
    reliability_issues: Mapped[list | None] = mapped_column(JSON)
    status_score: Mapped[float | None] = mapped_column(Float)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class QualityMetricDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_metric_definition"
    __table_args__ = (
        UniqueConstraint("quality_type", "code", name="uk_quality_type_metric_code"),
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
        UniqueConstraint("measurement_id", "metric_code", name="uk_measurement_metric"),
    )

    measurement_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    corrected_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(24))


class MeasurementRepeatReading(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_repeat_reading"
    __table_args__ = (
        UniqueConstraint(
            "measurement_id",
            "repeat_no",
            "metric_code",
            name="uk_measurement_repeat_metric",
        ),
    )

    measurement_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    repeat_no: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    corrected_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(24))
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    invalid_reason: Mapped[str | None] = mapped_column(String(240))


class QualityStandard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_standard"
    __table_args__ = (
        Index("ix_standard_match", "quality_type", "metric_code", "vehicle_model_id", "color_id"),
    )

    standard_no: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    standard_type: Mapped[str] = mapped_column(String(24), default="PRODUCTION", nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    vehicle_model_id: Mapped[str | None] = mapped_column(String(36))
    color_id: Mapped[str | None] = mapped_column(String(36))
    part_id: Mapped[str | None] = mapped_column(String(36))
    measurement_point_id: Mapped[str | None] = mapped_column(String(36))
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
            "target_family",
            name="uk_run_point_feature_target_version",
        ),
    )

    production_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    feature_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    target_family: Mapped[str] = mapped_column(
        String(32), default=QualityType.ORANGE_PEEL, nullable=False
    )
    feature_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    lineage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DatasetSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dataset_snapshot"
    __table_args__ = (
        UniqueConstraint("dataset_code", "version", name="uk_dataset_snapshot_version"),
    )

    dataset_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    split_strategy: Mapped[str] = mapped_column(String(48), nullable=False)
    group_key: Mapped[str] = mapped_column(String(32), nullable=False)
    holdout_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="BUILT", nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    train_sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    train_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cutoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    feature_names: Mapped[list] = mapped_column(JSON, nullable=False)
    lineage: Mapped[dict] = mapped_column(JSON, nullable=False)
    leakage_check: Mapped[dict] = mapped_column(JSON, nullable=False)
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DatasetSplitMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dataset_split_member"
    __table_args__ = (
        UniqueConstraint(
            "dataset_snapshot_id",
            "point_feature_snapshot_id",
            name="uk_dataset_feature_snapshot",
        ),
        Index("ix_dataset_split_group", "dataset_snapshot_id", "split", "group_value"),
    )

    dataset_snapshot_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    point_feature_snapshot_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    production_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    target_measurement_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    group_value: Mapped[str] = mapped_column(String(100), nullable=False)
    split: Mapped[str] = mapped_column(String(24), nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    feature_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_version"
    __table_args__ = (
        UniqueConstraint("model_code", "version", name="uk_model_version"),
    )

    model_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    dataset_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    model_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    evaluation_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    training_sample_count: Mapped[int] = mapped_column(default=0, nullable=False)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default=VersionStatus.DRAFT, nullable=False)


class ModelAcceptanceDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_acceptance_decision"
    __table_args__ = (
        Index("ix_model_acceptance_decision_time", "model_version_id", "decided_at"),
    )

    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dataset_snapshot_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False)
    checks: Mapped[dict] = mapped_column(JSON, nullable=False)
    decided_by: Mapped[str] = mapped_column(String(80), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)


class ModelApplicabilityScope(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_applicability_scope"
    __table_args__ = (
        UniqueConstraint(
            "model_version_id",
            "factory_id",
            "vehicle_model_id",
            "color_id",
            name="uk_model_applicability_context",
        ),
        Index("ix_model_applicability_status", "model_version_id", "status"),
    )

    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    factory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    vehicle_model_id: Mapped[str] = mapped_column(String(36), nullable=False)
    color_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="DATASET_DERIVED", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class ModelOodPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_ood_policy"
    __table_args__ = (
        UniqueConstraint("model_version_id", name="uk_model_ood_policy_version"),
    )

    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    max_abs_standardized_shift: Mapped[float] = mapped_column(Float, nullable=False)
    max_outlier_feature_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    min_feature_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    action: Mapped[str] = mapped_column(String(24), default="BLOCK", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class ModelAcceptancePolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_acceptance_policy"
    __table_args__ = (
        UniqueConstraint("policy_code", "version", name="uk_model_acceptance_policy_version"),
        Index(
            "ix_model_acceptance_policy_match",
            "factory_id",
            "target_metric",
            "status",
        ),
    )

    policy_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column("version_no", String(32), key="version", nullable=False)
    factory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(24), default="FACTORY_APPROVED", nullable=False)
    max_validation_rmse: Mapped[float] = mapped_column(Float, nullable=False)
    min_validation_r2: Mapped[float] = mapped_column(Float, nullable=False)
    min_train_groups: Mapped[int] = mapped_column(Integer, nullable=False)
    min_validation_groups: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    source_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class PredictionResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prediction_result"
    __table_args__ = (
        Index("ix_prediction_run_point", "production_run_id", "measurement_point_id"),
    )

    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    production_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float | None] = mapped_column(Float)
    upper_bound: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    applicability_status: Mapped[str] = mapped_column(
        String(24), default="LEGACY_UNGOVERNED", nullable=False
    )
    ood_status: Mapped[str] = mapped_column(
        String(24), default="LEGACY_UNGOVERNED", nullable=False
    )
    governance_evidence: Mapped[dict | None] = mapped_column(JSON)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DiagnosisResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diagnosis_result"

    prediction_result_id: Mapped[str | None] = mapped_column(String(36))
    production_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
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
    production_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    measurement_point_id: Mapped[str] = mapped_column(String(36), nullable=False
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

    recommendation_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
        UniqueConstraint("recommendation_id", name="uk_recommendation_evaluation"),
    )

    recommendation_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
        UniqueConstraint("endpoint_id", "source_event_id", name="uk_endpoint_source_event"),
        Index("ix_integration_event_status_time", "status", "created_at"),
    )

    event_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    endpoint_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
