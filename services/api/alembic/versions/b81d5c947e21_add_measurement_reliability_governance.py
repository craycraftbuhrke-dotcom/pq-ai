"""add measurement reliability governance

Revision ID: b81d5c947e21
Revises: 4f2c7a81d9b0
Create Date: 2026-06-13 08:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b81d5c947e21"
down_revision: str | None = "4f2c7a81d9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "measurement_instrument",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("manufacturer", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("instrument_type", sa.String(length=32), nullable=False),
        sa.Column("serial_no", sa.String(length=120), nullable=False),
        sa.Column("firmware_version", sa.String(length=64), nullable=True),
        sa.Column("supported_quality_types", sa.JSON(), nullable=False),
        sa.Column("calibration_required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("serial_no"),
    )
    op.create_table(
        "measurement_method",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("quality_type", sa.String(length=32), nullable=False),
        sa.Column("instrument_type", sa.String(length=32), nullable=False),
        sa.Column("method_type", sa.String(length=64), nullable=False),
        sa.Column("probe_code", sa.String(length=64), nullable=True),
        sa.Column("substrate_type", sa.String(length=80), nullable=True),
        sa.Column("geometry_class", sa.String(length=80), nullable=True),
        sa.Column("layer_scope", sa.String(length=80), nullable=True),
        sa.Column("requires_reference", sa.Boolean(), nullable=False),
        sa.Column("requires_direction", sa.Boolean(), nullable=False),
        sa.Column("minimum_repeats", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_measurement_method_version"),
    )
    op.create_table(
        "measurement_reference_standard",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("quality_type", sa.String(length=32), nullable=False),
        sa.Column("serial_no", sa.String(length=120), nullable=True),
        sa.Column("certificate_no", sa.String(length=120), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_values", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "measurement_import_profile",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("instrument_type", sa.String(length=32), nullable=False),
        sa.Column("quality_type", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("field_mapping", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_measurement_import_profile_version"),
    )
    op.create_table(
        "measurement_calibration_record",
        sa.Column("calibration_no", sa.String(length=64), nullable=False),
        sa.Column("instrument_id", sa.String(length=36), nullable=False),
        sa.Column("method_id", sa.String(length=36), nullable=True),
        sa.Column("reference_standard_id", sa.String(length=36), nullable=True),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.String(length=24), nullable=False),
        sa.Column("performed_by", sa.String(length=80), nullable=False),
        sa.Column("certificate_uri", sa.String(length=500), nullable=True),
        sa.Column("check_values", sa.JSON(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["measurement_instrument.id"]),
        sa.ForeignKeyConstraint(["method_id"], ["measurement_method.id"]),
        sa.ForeignKeyConstraint(["reference_standard_id"], ["measurement_reference_standard.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("calibration_no"),
    )
    op.create_index(
        "ix_calibration_instrument_time",
        "measurement_calibration_record",
        ["instrument_id", "calibrated_at"],
        unique=False,
    )
    with op.batch_alter_table("quality_measurement") as batch_op:
        batch_op.add_column(sa.Column("instrument_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("measurement_method_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("calibration_record_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("reference_standard_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("import_profile_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("measurement_direction", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("raw_file_uri", sa.String(length=500), nullable=True))
        batch_op.add_column(
            sa.Column(
                "reliability_status",
                sa.String(length=24),
                server_default="UNVERIFIED",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("reliability_issues", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_quality_measurement_instrument",
            "measurement_instrument",
            ["instrument_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_quality_measurement_method",
            "measurement_method",
            ["measurement_method_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_quality_measurement_calibration",
            "measurement_calibration_record",
            ["calibration_record_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_quality_measurement_reference",
            "measurement_reference_standard",
            ["reference_standard_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_quality_measurement_import_profile",
            "measurement_import_profile",
            ["import_profile_id"],
            ["id"],
        )
    op.create_table(
        "measurement_repeat_reading",
        sa.Column("measurement_id", sa.String(length=36), nullable=False),
        sa.Column("repeat_no", sa.Integer(), nullable=False),
        sa.Column("metric_code", sa.String(length=64), nullable=False),
        sa.Column("raw_value", sa.Float(), nullable=False),
        sa.Column("corrected_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("invalid_reason", sa.String(length=240), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["measurement_id"], ["quality_measurement.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "measurement_id",
            "repeat_no",
            "metric_code",
            name="uq_measurement_repeat_metric",
        ),
    )
    # Previously trained models did not require verified measurement provenance.
    op.execute("UPDATE model_version SET status = 'RETIRED' WHERE status = 'ACTIVE'")


def downgrade() -> None:
    op.drop_table("measurement_repeat_reading")
    with op.batch_alter_table("quality_measurement") as batch_op:
        batch_op.drop_constraint("fk_quality_measurement_import_profile", type_="foreignkey")
        batch_op.drop_constraint("fk_quality_measurement_reference", type_="foreignkey")
        batch_op.drop_constraint("fk_quality_measurement_calibration", type_="foreignkey")
        batch_op.drop_constraint("fk_quality_measurement_method", type_="foreignkey")
        batch_op.drop_constraint("fk_quality_measurement_instrument", type_="foreignkey")
        batch_op.drop_column("reliability_issues")
        batch_op.drop_column("reliability_status")
        batch_op.drop_column("raw_file_uri")
        batch_op.drop_column("measurement_direction")
        batch_op.drop_column("import_profile_id")
        batch_op.drop_column("reference_standard_id")
        batch_op.drop_column("calibration_record_id")
        batch_op.drop_column("measurement_method_id")
        batch_op.drop_column("instrument_id")
    op.drop_index("ix_calibration_instrument_time", table_name="measurement_calibration_record")
    op.drop_table("measurement_calibration_record")
    op.drop_table("measurement_import_profile")
    op.drop_table("measurement_reference_standard")
    op.drop_table("measurement_method")
    op.drop_table("measurement_instrument")
