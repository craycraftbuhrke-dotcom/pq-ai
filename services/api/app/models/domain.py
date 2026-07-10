from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, logical_fk


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
    password_hash: Mapped[str | None] = mapped_column(String(255))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uk_user_role"),)

    user_id: Mapped[str] = logical_fk("app_user.id", nullable=False)
    role_id: Mapped[str] = logical_fk("role.id", nullable=False)


class RolePermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uk_role_permission"),
    )

    role_id: Mapped[str] = logical_fk("role.id", nullable=False)
    permission_id: Mapped[str] = logical_fk("permission.id", nullable=False)


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_key"
    __table_args__ = (Index("idx_api_key_prefix", "key_prefix"),)

    user_id: Mapped[str] = logical_fk("app_user.id", nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_session"
    __table_args__ = (
        Index("idx_user_session_user", "user_id", "expires_at"),
    )

    user_id: Mapped[str] = logical_fk("app_user.id", nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    client_ip: Mapped[str | None] = mapped_column(String(64))


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_actor_time", "actor_user_id", "occurred_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )

    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[str | None] = logical_fk("app_user.id")
    actor_username: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column("action_type", String(100), nullable=False)
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

    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
    vehicle_model_id: Mapped[str] = logical_fk("vehicle_model.id", nullable=False)
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

    vehicle_model_id: Mapped[str] = logical_fk("vehicle_model.id", nullable=False)
    color_id: Mapped[str] = logical_fk("color.id", nullable=False)
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
    vehicle_model_id: Mapped[str] = logical_fk("vehicle_model.id", nullable=False)
    part_id: Mapped[str] = logical_fk("part.id", nullable=False)
    point_type: Mapped[str] = mapped_column(String(32), default="QUALITY", nullable=False)
    region: Mapped[str | None] = mapped_column(String(80))
    quality_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_match_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MeasurementPointLayout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Normalized body-map placement for a measurement point on TOP or SIDE view."""

    __tablename__ = "measurement_point_layout"
    __table_args__ = (
        UniqueConstraint("measurement_point_id", "body_view", name="uk_point_layout_view"),
        Index("idx_point_layout_view_status", "body_view", "row_status"),
    )

    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    body_view: Mapped[str] = mapped_column(String(16), nullable=False)
    layout_x: Mapped[float] = mapped_column(Float, nullable=False)
    layout_y: Mapped[float] = mapped_column(Float, nullable=False)
    grid_col: Mapped[int | None] = mapped_column(Integer)
    grid_row: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)


class MeasurementGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_group"
    __table_args__ = (
        UniqueConstraint("vehicle_model_id", "code", name="uk_group_model_code"),
    )

    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    vehicle_model_id: Mapped[str] = logical_fk("vehicle_model.id", nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_point_count: Mapped[int | None] = mapped_column()
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementGroupPoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_group_point"
    __table_args__ = (
        UniqueConstraint("measurement_group_id", "measurement_point_id", name="uk_group_point"),
    )

    measurement_group_id: Mapped[str] = logical_fk("measurement_group.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    sequence_no: Mapped[int] = mapped_column(default=0, nullable=False)


class SprayProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spray_program"
    __table_args__ = (
        UniqueConstraint("factory_id", "program_code", name="uk_factory_program_code"),
    )

    program_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
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

    spray_program_id: Mapped[str] = logical_fk("spray_program.id", nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default=VersionStatus.DRAFT, nullable=False)
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

    program_version_id: Mapped[str] = logical_fk("spray_program_version.id", nullable=False)
    vehicle_model_id: Mapped[str] = logical_fk("vehicle_model.id", nullable=False)


class ProgramColor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_color"
    __table_args__ = (
        UniqueConstraint("program_version_id", "color_id", name="uk_program_color"),
    )

    program_version_id: Mapped[str] = logical_fk("spray_program_version.id", nullable=False)
    color_id: Mapped[str] = logical_fk("color.id", nullable=False)


class ProcessRoute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "process_route"
    __table_args__ = (
        UniqueConstraint("factory_id", "route_code", "version", name="uk_process_route_ver"),
        Index("idx_process_route_status", "factory_id", "row_status"),
    )

    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
    route_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    route_type: Mapped[str] = mapped_column(String(24), default="3C3B", nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    bake_strategy: Mapped[str | None] = mapped_column(String(120))
    source_uri: Mapped[str | None] = mapped_column(String(500))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class ProcessRouteStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "process_route_step"
    __table_args__ = (
        UniqueConstraint("process_route_id", "sequence_no", name="uk_route_step_seq"),
        UniqueConstraint("process_route_id", "step_code", name="uk_route_step_code"),
    )

    process_route_id: Mapped[str] = logical_fk("process_route.id", nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    step_code: Mapped[str] = mapped_column(String(64), nullable=False)
    step_name: Mapped[str] = mapped_column(String(160), nullable=False)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False)
    coating_system: Mapped[str | None] = mapped_column(String(32))
    process_stage: Mapped[str | None] = mapped_column(String(32))
    station_code: Mapped[str | None] = mapped_column(String(64))
    upstream_step_code: Mapped[str | None] = mapped_column(String(64))
    downstream_step_code: Mapped[str | None] = mapped_column(String(64))
    is_ai_feature_source: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    control_requirements: Mapped[dict | None] = mapped_column(JSON)
    remark: Mapped[str | None] = mapped_column(Text)


class ProcessRouteApplicability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "process_route_applicability"
    __table_args__ = (
        UniqueConstraint(
            "process_route_id",
            "vehicle_model_id",
            "color_id",
            name="uk_route_model_color",
        ),
        Index("idx_route_applicability_status", "process_route_id", "row_status"),
    )

    process_route_id: Mapped[str] = logical_fk("process_route.id", nullable=False)
    vehicle_model_id: Mapped[str | None] = logical_fk("vehicle_model.id")
    color_id: Mapped[str | None] = logical_fk("color.id")
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


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


class ParameterConstraintSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parameter_constraint_source"
    __table_args__ = (
        UniqueConstraint("constraint_code", name="uk_param_constraint_code"),
        Index(
            "idx_param_constraint_lookup",
            "parameter_definition_id",
            "factory_id",
            "process_stage",
            "row_status",
        ),
    )

    parameter_definition_id: Mapped[str] = logical_fk("parameter_definition.id", nullable=False)
    factory_id: Mapped[str | None] = logical_fk("factory.id")
    process_stage: Mapped[str | None] = mapped_column(String(32))
    constraint_code: Mapped[str] = mapped_column(String(96), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    lower_limit: Mapped[float] = mapped_column(Float, nullable=False)
    upper_limit: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class Brush(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brush"
    __table_args__ = (
        UniqueConstraint("program_version_id", "brush_no", name="uk_program_brush_no"),
    )

    program_version_id: Mapped[str] = logical_fk("spray_program_version.id", nullable=False)
    brush_no: Mapped[str] = mapped_column(String(32), nullable=False)
    brush_table_no: Mapped[str] = mapped_column(String(64), nullable=False)
    spray_position: Mapped[str | None] = mapped_column(String(120))
    part_id: Mapped[str | None] = logical_fk("part.id")
    remark: Mapped[str | None] = mapped_column(Text)


class BrushParameter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brush_parameter"
    __table_args__ = (
        UniqueConstraint("brush_id", "parameter_code", name="uk_brush_parameter"),
    )

    brush_id: Mapped[str] = logical_fk("brush.id", nullable=False)
    parameter_definition_id: Mapped[str | None] = logical_fk("parameter_definition.id")
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

    brush_id: Mapped[str] = logical_fk("brush.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    overlap_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="EXPERT", nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DurrRobot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "durr_robot"
    __table_args__ = (UniqueConstraint("factory_id", "code", name="uk_factory_durr_robot"),)

    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    controller_software_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)


class DurrApplicationController(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "durr_application_controller"
    __table_args__ = (
        UniqueConstraint("factory_id", "code", name="uk_factory_durr_controller"),
    )

    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    software_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)


class DurrRotaryAtomizer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "durr_rotary_atomizer"
    __table_args__ = (
        UniqueConstraint("factory_id", "code", name="uk_factory_durr_atomizer"),
    )

    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
    controller_id: Mapped[str | None] = logical_fk("durr_application_controller.id")
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    bell_cup_type: Mapped[str | None] = mapped_column(String(120))
    bell_cup_code: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)


class ProgramDeviceConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_device_configuration"
    __table_args__ = (
        UniqueConstraint(
            "program_version_id",
            "configuration_version",
            name="uk_prog_device_config_ver",
        ),
    )

    program_version_id: Mapped[str] = logical_fk("spray_program_version.id", nullable=False)
    robot_id: Mapped[str] = logical_fk("durr_robot.id", nullable=False)
    atomizer_id: Mapped[str] = logical_fk("durr_rotary_atomizer.id", nullable=False)
    controller_id: Mapped[str] = logical_fk("durr_application_controller.id", nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
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

    program_version_id: Mapped[str] = logical_fk("spray_program_version.id", nullable=False)
    trajectory_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    coordinate_system: Mapped[str | None] = mapped_column(String(80))
    tcp_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
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

    trajectory_program_id: Mapped[str] = logical_fk("trajectory_program.id", nullable=False)
    segment_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    brush_id: Mapped[str | None] = logical_fk("brush.id")
    part_id: Mapped[str | None] = logical_fk("part.id")
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
            name="uk_prog_target_contrib_ver",
        ),
    )

    program_version_id: Mapped[str] = logical_fk("spray_program_version.id", nullable=False)
    target_family: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    method: Mapped[str] = mapped_column("method_code", String(32), nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
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
            name="uk_ver_point_contrib_src",
        ),
        CheckConstraint(
            "(brush_id IS NOT NULL AND path_segment_id IS NULL) OR "
            "(brush_id IS NULL AND path_segment_id IS NOT NULL)",
            name="ck_point_contribution_exactly_one_source",
        ),
    )

    contribution_version_id: Mapped[str] = logical_fk("point_contribution_version.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    brush_id: Mapped[str | None] = logical_fk("brush.id")
    path_segment_id: Mapped[str | None] = logical_fk("trajectory_path_segment.id")
    source_key: Mapped[str] = mapped_column(String(100), nullable=False)
    overlap_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False)
    validation_score: Mapped[float | None] = mapped_column(Float)
    evidence: Mapped[dict | None] = mapped_column(JSON)


class ContributionValidationStudy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contribution_validation"
    __table_args__ = (
        UniqueConstraint("contribution_version_id", "study_no", name="uk_contrib_val_study"),
        Index("idx_contrib_val_status", "contribution_version_id", "row_status"),
    )

    contribution_version_id: Mapped[str] = logical_fk("point_contribution_version.id", nullable=False)
    study_no: Mapped[str] = mapped_column(String(64), nullable=False)
    target_family: Mapped[str] = mapped_column(String(32), nullable=False)
    method: Mapped[str] = mapped_column("method_code", String(32), nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    sample_count: Mapped[int | None] = mapped_column(Integer)
    validation_score: Mapped[float | None] = mapped_column(Float)
    evidence_uri: Mapped[str | None] = mapped_column(String(500))
    evidence_payload: Mapped[dict | None] = mapped_column(JSON)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class TrajectorySegmentGeometry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trajectory_segment_geometry"
    __table_args__ = (
        UniqueConstraint("path_segment_id", "geometry_version", name="uk_path_segment_geometry"),
        Index("idx_path_geometry_status", "path_segment_id", "row_status"),
    )

    path_segment_id: Mapped[str] = logical_fk("trajectory_path_segment.id", nullable=False)
    geometry_version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_import_job_id: Mapped[str | None] = logical_fk("file_import_job.id")
    start_position: Mapped[dict | None] = mapped_column(JSON)
    end_position: Mapped[dict | None] = mapped_column(JSON)
    orientation: Mapped[dict | None] = mapped_column(JSON)
    normal_vector: Mapped[dict | None] = mapped_column(JSON)
    gun_distance: Mapped[float | None] = mapped_column(Float)
    path_spacing: Mapped[float | None] = mapped_column(Float)
    overlap_ratio: Mapped[float | None] = mapped_column(Float)
    collision_risk_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    evidence_uri: Mapped[str | None] = mapped_column(String(500))
    remark: Mapped[str | None] = mapped_column(Text)


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


class FileImportProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "file_import_profile"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uk_file_import_profile"),
        Index("idx_file_import_profile_domain", "domain_type", "row_status"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    domain_type: Mapped[str] = mapped_column(String(48), nullable=False)
    parser_type: Mapped[str] = mapped_column(String(32), default="CSV", nullable=False)
    target_resource: Mapped[str] = mapped_column(String(80), nullable=False)
    field_mapping: Mapped[dict] = mapped_column(JSON, nullable=False)
    required_fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    validation_rules: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class FileImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "file_import_job"
    __table_args__ = (
        UniqueConstraint("import_no", name="uk_file_import_job_no"),
        Index("idx_file_import_job_status", "domain_type", "row_status", "submitted_at"),
    )

    import_no: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_id: Mapped[str] = logical_fk("file_import_profile.id", nullable=False)
    domain_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(240), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    source_checksum: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column("row_status", String(24), default="PREVIEWED", nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    preview_payload: Mapped[dict | None] = mapped_column(JSON)
    error_report: Mapped[dict | None] = mapped_column(JSON)
    submitted_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replay_of_job_id: Mapped[str | None] = logical_fk("file_import_job.id")
    remark: Mapped[str | None] = mapped_column(Text)


class SupplierMaterialSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_mat_submission"
    __table_args__ = (
        UniqueConstraint("submission_no", name="uk_supplier_mat_submission"),
        Index("idx_supplier_mat_status", "supplier", "row_status", "submitted_at"),
    )

    submission_no: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier: Mapped[str] = mapped_column(String(120), nullable=False)
    material_batch_id: Mapped[str | None] = logical_fk("material_batch.id")
    material_code: Mapped[str] = mapped_column(String(64), nullable=False)
    material_name: Mapped[str | None] = mapped_column(String(120))
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    profile_id: Mapped[str | None] = logical_fk("file_import_profile.id")
    status: Mapped[str] = mapped_column("row_status", String(24), default="SUBMITTED", nullable=False)
    submitted_by: Mapped[str] = mapped_column(String(80), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(80))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    field_values: Mapped[dict | None] = mapped_column(JSON)
    validation_result: Mapped[dict | None] = mapped_column(JSON)
    deviation_decision: Mapped[str | None] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(Text)


class SupplierMaterialIssue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_mat_issue"
    __table_args__ = (
        UniqueConstraint("issue_no", name="uk_supplier_mat_issue"),
        Index("idx_supplier_issue_status", "row_status", "due_at"),
    )

    issue_no: Mapped[str] = mapped_column(String(64), nullable=False)
    submission_id: Mapped[str | None] = logical_fk("supplier_mat_submission.id")
    material_batch_id: Mapped[str | None] = logical_fk("material_batch.id")
    issue_type: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), default="MEDIUM", nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="OPEN", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    containment_action: Mapped[str | None] = mapped_column(Text)
    supplier_response: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(80))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MaterialCharacteristicDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mat_char_definition"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    target_families: Mapped[list] = mapped_column(JSON, nullable=False)
    is_model_feature: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class MaterialTestMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_test_method"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uk_material_test_method_version"),
    )

    characteristic_definition_id: Mapped[str] = logical_fk("mat_char_definition.id", nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    method_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    procedure_uri: Mapped[str | None] = mapped_column(String(500))
    conditions: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class MaterialSpecification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_specification"
    __table_args__ = (
        UniqueConstraint(
            "material_code",
            "characteristic_definition_id",
            "method_id",
            "version",
            name="uk_mat_spec_ver",
        ),
    )

    material_code: Mapped[str] = mapped_column(String(64), nullable=False)
    characteristic_definition_id: Mapped[str] = logical_fk("mat_char_definition.id", nullable=False)
    method_id: Mapped[str] = logical_fk("material_test_method.id", nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    lower_limit: Mapped[float | None] = mapped_column(Float)
    upper_limit: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class MaterialCharacteristicApplicability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mat_char_applicability"
    __table_args__ = (
        UniqueConstraint(
            "characteristic_definition_id",
            "material_type",
            "process_stage",
            "target_family",
            name="uk_mat_char_applicability",
        ),
    )

    characteristic_definition_id: Mapped[str] = logical_fk("mat_char_definition.id", nullable=False)
    material_type: Mapped[str] = mapped_column(String(24), nullable=False)
    process_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    target_family: Mapped[str] = mapped_column(String(32), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class MaterialBatchTestResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_batch_test_result"
    __table_args__ = (
        Index(
            "idx_mat_result_batch_char_time",
            "material_batch_id",
            "characteristic_definition_id",
            "tested_at",
        ),
    )

    result_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    material_batch_id: Mapped[str] = logical_fk("material_batch.id", nullable=False)
    characteristic_definition_id: Mapped[str] = logical_fk("mat_char_definition.id", nullable=False)
    method_id: Mapped[str] = logical_fk("material_test_method.id", nullable=False)
    specification_id: Mapped[str | None] = logical_fk("material_specification.id")
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
        Index("idx_production_run_context", "factory_id", "vehicle_model_id", "color_id"),
        Index("idx_production_body_no", "body_no"),
    )

    run_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    body_no: Mapped[str | None] = mapped_column(String(64))
    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
    vehicle_model_id: Mapped[str] = logical_fk("vehicle_model.id", nullable=False)
    color_id: Mapped[str] = logical_fk("color.id", nullable=False)
    shift: Mapped[str | None] = mapped_column(String(24))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context_values: Mapped[dict | None] = mapped_column(JSON)


class ProductionStageRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_stage_run"
    __table_args__ = (
        UniqueConstraint("production_run_id", "process_stage", name="uk_run_stage"),
    )

    production_run_id: Mapped[str] = logical_fk("production_run.id", nullable=False)
    process_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    program_version_id: Mapped[str] = logical_fk("spray_program_version.id", nullable=False)
    material_batch_id: Mapped[str | None] = logical_fk("material_batch.id")
    actual_parameters: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column("row_status", String(24), default="COMPLETED", nullable=False)


class ProductionDeviceExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_device_execution"
    __table_args__ = (
        UniqueConstraint("production_stage_run_id", name="uk_stage_device_execution"),
    )

    production_stage_run_id: Mapped[str] = logical_fk("production_stage_run.id", nullable=False)
    device_configuration_id: Mapped[str] = logical_fk("program_device_configuration.id", nullable=False)
    trajectory_program_id: Mapped[str] = logical_fk("trajectory_program.id", nullable=False)
    executed_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column("row_status", String(24), default="COMPLETED", nullable=False)
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

    device_execution_id: Mapped[str] = logical_fk("production_device_execution.id", nullable=False)
    path_segment_id: Mapped[str] = logical_fk("trajectory_path_segment.id", nullable=False)
    actual_speed: Mapped[float | None] = mapped_column(Float)
    speed_unit: Mapped[str | None] = mapped_column(String(24))
    trigger_state: Mapped[str | None] = mapped_column(String(24))
    actual_values: Mapped[dict | None] = mapped_column(JSON)


class ActualParameter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actual_parameter"
    __table_args__ = (
        Index("idx_actual_parameter_stage_code", "production_stage_run_id", "parameter_code"),
    )

    production_stage_run_id: Mapped[str] = logical_fk("production_stage_run.id", nullable=False)
    brush_id: Mapped[str | None] = logical_fk("brush.id")
    parameter_definition_id: Mapped[str | None] = logical_fk("parameter_definition.id")
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
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementProbe(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_probe"
    __table_args__ = (
        UniqueConstraint("instrument_id", "code", name="uk_instrument_probe_code"),
        Index("idx_measurement_probe_status", "instrument_id", "row_status"),
    )

    instrument_id: Mapped[str] = logical_fk("measurement_instrument.id", nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    probe_type: Mapped[str] = mapped_column(String(64), nullable=False)
    serial_no: Mapped[str | None] = mapped_column(String(120))
    substrate_type: Mapped[str | None] = mapped_column(String(80))
    geometry_class: Mapped[str | None] = mapped_column(String(80))
    layer_scope: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_method"
    __table_args__ = (UniqueConstraint("code", "version", name="uk_measurement_method_version"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
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
    status: Mapped[str] = mapped_column("row_status", String(24), default="ACTIVE", nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementImportProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_import_profile"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uk_meas_import_profile_ver"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    field_mapping: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementCalibrationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_calibration_record"
    __table_args__ = (Index("idx_calibration_instrument_time", "instrument_id", "calibrated_at"),)

    calibration_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    instrument_id: Mapped[str] = logical_fk("measurement_instrument.id", nullable=False)
    method_id: Mapped[str | None] = logical_fk("measurement_method.id")
    reference_standard_id: Mapped[str | None] = logical_fk("measurement_reference_standard.id")
    calibrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String(24), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(80), nullable=False)
    certificate_uri: Mapped[str | None] = mapped_column(String(500))
    check_values: Mapped[dict | None] = mapped_column(JSON)
    remark: Mapped[str | None] = mapped_column(Text)


class MeasurementMsaStudy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "measurement_msa_study"
    __table_args__ = (
        UniqueConstraint("study_no", name="uk_measurement_msa_study"),
        Index("idx_measurement_msa_status", "instrument_id", "result"),
    )

    study_no: Mapped[str] = mapped_column(String(64), nullable=False)
    instrument_id: Mapped[str] = logical_fk("measurement_instrument.id", nullable=False)
    probe_id: Mapped[str | None] = logical_fk("measurement_probe.id")
    method_id: Mapped[str | None] = logical_fk("measurement_method.id")
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    study_type: Mapped[str] = mapped_column(String(32), default="GRR", nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    operator_count: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat_count: Mapped[int] = mapped_column(Integer, nullable=False)
    grr_percent: Mapped[float | None] = mapped_column(Float)
    ndc: Mapped[float | None] = mapped_column(Float)
    result: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    study_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_results: Mapped[dict | None] = mapped_column(JSON)
    remark: Mapped[str | None] = mapped_column(Text)


class QualityMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_measurement"
    __table_args__ = (
        Index("idx_quality_point_time", "measurement_point_id", "measured_at"),
    )

    data_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    production_run_id: Mapped[str] = logical_fk("production_run.id", nullable=False)
    measurement_group_id: Mapped[str | None] = logical_fk("measurement_group.id")
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    data_type: Mapped[str] = mapped_column(String(24), default="TEST", nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    measured_by: Mapped[str | None] = mapped_column(String(80))
    device_code: Mapped[str | None] = mapped_column(String(64))
    instrument_id: Mapped[str | None] = logical_fk("measurement_instrument.id")
    measurement_probe_id: Mapped[str | None] = logical_fk("measurement_probe.id")
    measurement_method_id: Mapped[str | None] = logical_fk("measurement_method.id")
    calibration_record_id: Mapped[str | None] = logical_fk("measurement_calibration_record.id")
    reference_standard_id: Mapped[str | None] = logical_fk("measurement_reference_standard.id")
    import_profile_id: Mapped[str | None] = logical_fk("measurement_import_profile.id")
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

    measurement_id: Mapped[str] = logical_fk("quality_measurement.id", nullable=False)
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

    measurement_id: Mapped[str] = logical_fk("quality_measurement.id", nullable=False)
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
        Index("idx_standard_match", "quality_type", "metric_code", "vehicle_model_id", "color_id"),
    )

    standard_no: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    standard_type: Mapped[str] = mapped_column(String(24), default="PRODUCTION", nullable=False)
    quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    vehicle_model_id: Mapped[str | None] = logical_fk("vehicle_model.id")
    color_id: Mapped[str | None] = logical_fk("color.id")
    part_id: Mapped[str | None] = logical_fk("part.id")
    measurement_point_id: Mapped[str | None] = logical_fk("measurement_point.id")
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
            name="uk_run_point_feature_ver",
        ),
    )

    production_run_id: Mapped[str] = logical_fk("production_run.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
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
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    split_strategy: Mapped[str] = mapped_column(String(48), nullable=False)
    group_key: Mapped[str] = mapped_column(String(32), nullable=False)
    holdout_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="BUILT", nullable=False)
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
        Index("idx_dataset_split_group", "dataset_snapshot_id", "split", "group_value"),
    )

    dataset_snapshot_id: Mapped[str] = logical_fk("dataset_snapshot.id", nullable=False)
    point_feature_snapshot_id: Mapped[str] = logical_fk("point_feature_snapshot.id", nullable=False)
    production_run_id: Mapped[str] = logical_fk("production_run.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    target_measurement_id: Mapped[str] = logical_fk("quality_measurement.id", nullable=False)
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
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    dataset_snapshot_id: Mapped[str | None] = logical_fk("dataset_snapshot.id")
    model_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    evaluation_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    training_sample_count: Mapped[int] = mapped_column(default=0, nullable=False)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column("row_status", String(24), default=VersionStatus.DRAFT, nullable=False)


class ModelValidationFold(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_validation_fold"
    __table_args__ = (
        UniqueConstraint(
            "model_version_id",
            "validation_axis",
            "fold_key",
            name="uk_model_validation_fold",
        ),
        Index("idx_model_validation_axis", "model_version_id", "validation_axis", "row_status"),
    )

    model_version_id: Mapped[str] = logical_fk("model_version.id", nullable=False)
    dataset_snapshot_id: Mapped[str] = logical_fk("dataset_snapshot.id", nullable=False)
    validation_axis: Mapped[str] = mapped_column(String(48), nullable=False)
    fold_key: Mapped[str] = mapped_column(String(120), nullable=False)
    train_sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    train_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(32), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_artifact"
    __table_args__ = (
        UniqueConstraint(
            "model_version_id",
            "artifact_type",
            name="uk_model_artifact_type",
        ),
        Index("idx_model_artifact_status", "model_version_id", "row_status"),
    )

    model_version_id: Mapped[str] = logical_fk("model_version.id", nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(48), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), default="MYSQL", nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="REGISTERED", nullable=False)
    created_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class ModelAcceptanceDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_acceptance_decision"
    __table_args__ = (
        Index("idx_model_accept_decision_time", "model_version_id", "decided_at"),
    )

    model_version_id: Mapped[str] = logical_fk("model_version.id", nullable=False)
    dataset_snapshot_id: Mapped[str] = logical_fk("dataset_snapshot.id", nullable=False)
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
        Index("idx_model_applicability_status", "model_version_id", "row_status"),
    )

    model_version_id: Mapped[str] = logical_fk("model_version.id", nullable=False)
    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
    vehicle_model_id: Mapped[str] = logical_fk("vehicle_model.id", nullable=False)
    color_id: Mapped[str] = logical_fk("color.id", nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="PENDING", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="DATASET_DERIVED", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class ModelOodPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_ood_policy"
    __table_args__ = (
        UniqueConstraint("model_version_id", name="uk_model_ood_policy_version"),
    )

    model_version_id: Mapped[str] = logical_fk("model_version.id", nullable=False)
    max_abs_standardized_shift: Mapped[float] = mapped_column(Float, nullable=False)
    max_outlier_feature_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    min_feature_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    action: Mapped[str] = mapped_column("action_type", String(24), default="BLOCK", nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="PENDING", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class ModelAcceptancePolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_acceptance_policy"
    __table_args__ = (
        UniqueConstraint("policy_code", "version", name="uk_model_accept_policy_ver"),
        Index(
            "idx_model_accept_policy_match",
            "factory_id",
            "target_metric",
            "row_status",
        ),
    )

    policy_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    factory_id: Mapped[str] = logical_fk("factory.id", nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(24), default="FACTORY_APPROVED", nullable=False)
    max_validation_rmse: Mapped[float] = mapped_column(Float, nullable=False)
    min_validation_r2: Mapped[float] = mapped_column(Float, nullable=False)
    min_train_groups: Mapped[int] = mapped_column(Integer, nullable=False)
    min_validation_groups: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    source_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class PredictionResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prediction_result"
    __table_args__ = (
        Index("idx_prediction_run_point", "production_run_id", "measurement_point_id"),
    )

    model_version_id: Mapped[str] = logical_fk("model_version.id", nullable=False)
    production_run_id: Mapped[str] = logical_fk("production_run.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
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

    prediction_result_id: Mapped[str | None] = logical_fk("prediction_result.id")
    production_run_id: Mapped[str] = logical_fk("production_run.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    factor_contributions: Mapped[list] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    causality_status: Mapped[str] = mapped_column(
        String(24), default="CORRELATION_ONLY", nullable=False
    )


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation"
    __table_args__ = (Index("idx_recommendation_status", "row_status", "created_at"),)

    recommendation_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    production_run_id: Mapped[str] = logical_fk("production_run.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    target_quality_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    diagnosis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column("row_status", 
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

    recommendation_id: Mapped[str] = logical_fk("recommendation.id", nullable=False)
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
    constraint_source_id: Mapped[str | None] = logical_fk("parameter_constraint_source.id")
    constraint_source_code: Mapped[str | None] = mapped_column(String(96))
    constraint_source_version: Mapped[str | None] = mapped_column(String(32))
    constraint_source_type: Mapped[str | None] = mapped_column(String(32))
    constraint_source_uri: Mapped[str | None] = mapped_column(String(500))


class ControlledTrial(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "controlled_trial"
    __table_args__ = (
        UniqueConstraint("trial_no", name="uk_controlled_trial_no"),
        UniqueConstraint("recommendation_id", name="uk_trial_recommendation"),
        Index("idx_controlled_trial_status", "row_status", "created_at"),
    )

    recommendation_id: Mapped[str] = logical_fk("recommendation.id", nullable=False)
    trial_no: Mapped[str] = mapped_column(String(64), nullable=False)
    production_run_id: Mapped[str] = logical_fk("production_run.id", nullable=False)
    measurement_point_id: Mapped[str] = logical_fk("measurement_point.id", nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # 计划阶段文档：合并 hypothesis / expected_outcome / risk_assessment / rollback_plan / sustained_observation_plan
    plan_document: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    constraint_evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="PLANNED", nullable=False)
    requested_by: Mapped[str] = mapped_column(String(80), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 执行阶段文档：合并 approval_comment / completion_summary
    execution_document: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ---- 业务字段兼容层：把 plan_document / execution_document 展平为 7 个字段 ----
    # 保持业务代码、Pydantic Schema、API 契约、前端字段名 100% 不变
    _PLAN_FIELDS = (
        "hypothesis",
        "expected_outcome",
        "risk_assessment",
        "rollback_plan",
        "sustained_observation_plan",
    )
    _EXECUTION_FIELDS = ("approval_comment", "completion_summary")

    def __init__(self, **kwargs):
        # 允许调用方以 hypothesis=... / expected_outcome=... 等平铺关键字构造对象，
        # 内部合并到 plan_document / execution_document 两个 JSON 列。
        plan_doc = dict(kwargs.pop("plan_document", None) or {})
        for field in self._PLAN_FIELDS:
            if field in kwargs:
                value = kwargs.pop(field)
                plan_doc[field] = value if value is not None else ""
        exec_doc = dict(kwargs.pop("execution_document", None) or {})
        for field in self._EXECUTION_FIELDS:
            if field in kwargs:
                value = kwargs.pop(field)
                if value is None:
                    exec_doc.pop(field, None)
                else:
                    exec_doc[field] = value
        if plan_doc:
            kwargs["plan_document"] = plan_doc
        if exec_doc:
            kwargs["execution_document"] = exec_doc
        super().__init__(**kwargs)

    def _plan_get(self, key: str) -> str:
        doc = self.plan_document or {}
        value = doc.get(key)
        return value if value is not None else ""

    def _plan_set(self, key: str, value: str | None) -> None:
        doc = dict(self.plan_document or {})
        doc[key] = value if value is not None else ""
        self.plan_document = doc

    def _exec_get(self, key: str) -> str | None:
        doc = self.execution_document or {}
        return doc.get(key)

    def _exec_set(self, key: str, value: str | None) -> None:
        doc = dict(self.execution_document or {})
        if value is None:
            doc.pop(key, None)
        else:
            doc[key] = value
        self.execution_document = doc if doc else None

    # 计划阶段 5 字段（NOT NULL 语义，缺失时返回 ""）
    @property
    def hypothesis(self) -> str:
        return self._plan_get("hypothesis")

    @hypothesis.setter
    def hypothesis(self, value: str | None) -> None:
        self._plan_set("hypothesis", value)

    @property
    def expected_outcome(self) -> str:
        return self._plan_get("expected_outcome")

    @expected_outcome.setter
    def expected_outcome(self, value: str | None) -> None:
        self._plan_set("expected_outcome", value)

    @property
    def risk_assessment(self) -> str:
        return self._plan_get("risk_assessment")

    @risk_assessment.setter
    def risk_assessment(self, value: str | None) -> None:
        self._plan_set("risk_assessment", value)

    @property
    def rollback_plan(self) -> str:
        return self._plan_get("rollback_plan")

    @rollback_plan.setter
    def rollback_plan(self, value: str | None) -> None:
        self._plan_set("rollback_plan", value)

    @property
    def sustained_observation_plan(self) -> str:
        return self._plan_get("sustained_observation_plan")

    @sustained_observation_plan.setter
    def sustained_observation_plan(self, value: str | None) -> None:
        self._plan_set("sustained_observation_plan", value)

    # 执行阶段 2 字段（可空）
    @property
    def approval_comment(self) -> str | None:
        return self._exec_get("approval_comment")

    @approval_comment.setter
    def approval_comment(self, value: str | None) -> None:
        self._exec_set("approval_comment", value)

    @property
    def completion_summary(self) -> str | None:
        return self._exec_get("completion_summary")

    @completion_summary.setter
    def completion_summary(self, value: str | None) -> None:
        self._exec_set("completion_summary", value)


class ProgramRollbackExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_rollback_execution"
    __table_args__ = (
        UniqueConstraint("controlled_trial_id", name="uk_rollback_controlled_trial"),
        UniqueConstraint("rollback_no", name="uk_program_rollback_no"),
        Index("idx_program_rollback_status", "row_status", "executed_at"),
    )

    rollback_no: Mapped[str] = mapped_column(String(64), nullable=False)
    recommendation_id: Mapped[str] = logical_fk("recommendation.id", nullable=False)
    controlled_trial_id: Mapped[str] = logical_fk("controlled_trial.id", nullable=False)
    rollback_to_program_version_id: Mapped[str | None] = logical_fk("spray_program_version.id")
    rollback_reason: Mapped[str] = mapped_column(Text, nullable=False)
    execution_note: Mapped[str | None] = mapped_column(Text)
    executed_by: Mapped[str] = mapped_column(String(80), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="EXECUTED", nullable=False)
    action_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    verified_by: Mapped[str | None] = mapped_column(String(80))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_comment: Mapped[str | None] = mapped_column(Text)


class ClosedLoopEvaluation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "closed_loop_evaluation"
    __table_args__ = (
        UniqueConstraint("recommendation_id", name="uk_recommendation_evaluation"),
    )

    recommendation_id: Mapped[str] = logical_fk("recommendation.id", nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    verified_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    is_effective: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by: Mapped[str] = mapped_column(String(80), nullable=False)
    conclusion: Mapped[str | None] = mapped_column(Text)


class QualityIssueTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_issue_task"
    __table_args__ = (
        UniqueConstraint("task_no", name="uk_quality_issue_task_no"),
        Index("idx_quality_issue_status", "row_status", "severity", "created_at"),
        Index("idx_quality_issue_context", "factory_id", "vehicle_model_id", "color_id"),
    )

    task_no: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), default="QUALITY_ISSUE", nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="OPEN", nullable=False)
    severity: Mapped[str] = mapped_column(String(24), default="MEDIUM", nullable=False)
    factory_id: Mapped[str | None] = logical_fk("factory.id")
    vehicle_model_id: Mapped[str | None] = logical_fk("vehicle_model.id")
    color_id: Mapped[str | None] = logical_fk("color.id")
    production_run_id: Mapped[str | None] = logical_fk("production_run.id")
    measurement_point_id: Mapped[str | None] = logical_fk("measurement_point.id")
    quality_measurement_id: Mapped[str | None] = logical_fk("quality_measurement.id")
    material_batch_id: Mapped[str | None] = logical_fk("material_batch.id")
    recommendation_id: Mapped[str | None] = logical_fk("recommendation.id")
    controlled_trial_id: Mapped[str | None] = logical_fk("controlled_trial.id")
    process_stage: Mapped[str | None] = mapped_column(String(32))
    target_quality_type: Mapped[str | None] = mapped_column(String(32))
    target_metric: Mapped[str | None] = mapped_column(String(64))
    owner_role: Mapped[str | None] = mapped_column(String(64))
    owner_user_id: Mapped[str | None] = logical_fk("app_user.id")
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    suspected_cause: Mapped[str | None] = mapped_column(Text)
    conclusion: Mapped[str | None] = mapped_column(Text)
    causality_status: Mapped[str] = mapped_column(
        String(32), default="CORRELATION_ONLY", nullable=False
    )
    data_quality_status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    material_status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    durr_execution_status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSON)


class QualityIssueEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_issue_evidence"
    __table_args__ = (
        Index("idx_quality_issue_evidence", "task_id", "evidence_type"),
    )

    task_id: Mapped[str] = logical_fk("quality_issue_task.id", nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(36))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_payload: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)
    causality_status: Mapped[str] = mapped_column(
        String(32), default="CORRELATION_ONLY", nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)


class QualityIssueComment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_issue_comment"
    __table_args__ = (
        Index("idx_quality_issue_comment", "task_id", "created_at"),
    )

    task_id: Mapped[str] = logical_fk("quality_issue_task.id", nullable=False)
    author: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str | None] = mapped_column("role_code", String(64))
    comment_type: Mapped[str] = mapped_column(String(32), default="COMMENT", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class EngineeringKnowledgeEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "eng_knowledge_entry"
    __table_args__ = (
        UniqueConstraint("entry_code", "version", name="uk_eng_knowledge_entry"),
        Index("idx_eng_knowledge_target", "target_quality_type", "metric_code", "row_status"),
    )

    entry_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(48), nullable=False)
    target_quality_type: Mapped[str | None] = mapped_column(String(32))
    metric_code: Mapped[str | None] = mapped_column(String(64))
    symptom_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis_rule: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_checks: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    related_parameters: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_level: Mapped[str] = mapped_column(String(32), default="RULE", nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="DRAFT", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(80))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)


class ModelExplanation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_explanation"
    __table_args__ = (
        Index("idx_model_explanation_target", "model_version_id", "explanation_type"),
    )

    model_version_id: Mapped[str] = logical_fk("model_version.id", nullable=False)
    prediction_result_id: Mapped[str | None] = logical_fk("prediction_result.id")
    explanation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_impacts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sensitivity_grid: Mapped[dict | None] = mapped_column(JSON)
    uncertainty: Mapped[dict | None] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)


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
        Index("idx_integration_status_time", "row_status", "created_at"),
    )

    event_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    endpoint_id: Mapped[str] = logical_fk("integration_endpoint.id", nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(24), default="INBOUND", nullable=False)
    status: Mapped[str] = mapped_column("row_status", String(24), default="PENDING", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    mapped_payload: Mapped[dict | None] = mapped_column(JSON)
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=3, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
