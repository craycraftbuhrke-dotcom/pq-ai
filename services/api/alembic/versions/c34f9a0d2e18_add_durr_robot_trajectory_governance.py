"""add durr robot trajectory governance

Revision ID: c34f9a0d2e18
Revises: b81d5c947e21
Create Date: 2026-06-13 10:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c34f9a0d2e18"
down_revision: str | None = "b81d5c947e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "durr_robot",
        sa.Column("factory_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("serial_no", sa.String(length=120), nullable=False),
        sa.Column("controller_software_version", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["factory_id"], ["factory.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("factory_id", "code", name="uq_factory_durr_robot"),
        sa.UniqueConstraint("serial_no"),
    )
    op.create_table(
        "durr_application_controller",
        sa.Column("factory_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("serial_no", sa.String(length=120), nullable=False),
        sa.Column("software_version", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["factory_id"], ["factory.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("factory_id", "code", name="uq_factory_durr_controller"),
        sa.UniqueConstraint("serial_no"),
    )
    op.create_table(
        "durr_rotary_atomizer",
        sa.Column("factory_id", sa.String(length=36), nullable=False),
        sa.Column("controller_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("serial_no", sa.String(length=120), nullable=False),
        sa.Column("bell_cup_type", sa.String(length=120), nullable=True),
        sa.Column("bell_cup_code", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["controller_id"], ["durr_application_controller.id"]),
        sa.ForeignKeyConstraint(["factory_id"], ["factory.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("factory_id", "code", name="uq_factory_durr_atomizer"),
        sa.UniqueConstraint("serial_no"),
    )
    op.create_table(
        "program_device_configuration",
        sa.Column("program_version_id", sa.String(length=36), nullable=False),
        sa.Column("robot_id", sa.String(length=36), nullable=False),
        sa.Column("atomizer_id", sa.String(length=36), nullable=False),
        sa.Column("controller_id", sa.String(length=36), nullable=False),
        sa.Column("configuration_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=True),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["atomizer_id"], ["durr_rotary_atomizer.id"]),
        sa.ForeignKeyConstraint(["controller_id"], ["durr_application_controller.id"]),
        sa.ForeignKeyConstraint(["program_version_id"], ["spray_program_version.id"]),
        sa.ForeignKeyConstraint(["robot_id"], ["durr_robot.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "program_version_id",
            "configuration_version",
            name="uq_program_device_configuration_version",
        ),
    )
    op.create_table(
        "trajectory_program",
        sa.Column("program_version_id", sa.String(length=36), nullable=False),
        sa.Column("trajectory_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("coordinate_system", sa.String(length=80), nullable=True),
        sa.Column("tcp_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=True),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["program_version_id"], ["spray_program_version.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "program_version_id",
            "trajectory_code",
            "version",
            name="uq_program_trajectory_version",
        ),
    )
    op.create_table(
        "trajectory_path_segment",
        sa.Column("trajectory_program_id", sa.String(length=36), nullable=False),
        sa.Column("segment_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brush_id", sa.String(length=36), nullable=True),
        sa.Column("part_id", sa.String(length=36), nullable=True),
        sa.Column("tcp_name", sa.String(length=120), nullable=True),
        sa.Column("configured_speed", sa.Float(), nullable=True),
        sa.Column("speed_unit", sa.String(length=24), nullable=True),
        sa.Column("start_position", sa.JSON(), nullable=True),
        sa.Column("end_position", sa.JSON(), nullable=True),
        sa.Column("orientation", sa.JSON(), nullable=True),
        sa.Column("trigger_state", sa.String(length=24), nullable=False),
        sa.Column("trigger_start_ms", sa.Float(), nullable=True),
        sa.Column("trigger_end_ms", sa.Float(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["brush_id"], ["brush.id"]),
        sa.ForeignKeyConstraint(["part_id"], ["part.id"]),
        sa.ForeignKeyConstraint(["trajectory_program_id"], ["trajectory_program.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trajectory_program_id",
            "segment_no",
            name="uq_trajectory_path_segment_no",
        ),
    )
    op.create_table(
        "point_contribution_version",
        sa.Column("program_version_id", sa.String(length=36), nullable=False),
        sa.Column("target_family", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("evidence_uri", sa.String(length=500), nullable=True),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["program_version_id"], ["spray_program_version.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "program_version_id",
            "target_family",
            "version",
            name="uq_program_target_contribution_version",
        ),
    )
    op.create_table(
        "point_contribution_entry",
        sa.Column("contribution_version_id", sa.String(length=36), nullable=False),
        sa.Column("measurement_point_id", sa.String(length=36), nullable=False),
        sa.Column("brush_id", sa.String(length=36), nullable=True),
        sa.Column("path_segment_id", sa.String(length=36), nullable=True),
        sa.Column("source_key", sa.String(length=100), nullable=False),
        sa.Column("overlap_ratio", sa.Float(), nullable=False),
        sa.Column("contribution_weight", sa.Float(), nullable=False),
        sa.Column("validation_score", sa.Float(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "(brush_id IS NOT NULL AND path_segment_id IS NULL) OR "
            "(brush_id IS NULL AND path_segment_id IS NOT NULL)",
            name="ck_point_contribution_exactly_one_source",
        ),
        sa.ForeignKeyConstraint(["brush_id"], ["brush.id"]),
        sa.ForeignKeyConstraint(["contribution_version_id"], ["point_contribution_version.id"]),
        sa.ForeignKeyConstraint(["measurement_point_id"], ["measurement_point.id"]),
        sa.ForeignKeyConstraint(["path_segment_id"], ["trajectory_path_segment.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "contribution_version_id",
            "measurement_point_id",
            "source_key",
            name="uq_version_point_contribution_source",
        ),
    )
    op.create_table(
        "production_device_execution",
        sa.Column("production_stage_run_id", sa.String(length=36), nullable=False),
        sa.Column("device_configuration_id", sa.String(length=36), nullable=False),
        sa.Column("trajectory_program_id", sa.String(length=36), nullable=False),
        sa.Column("executed_checksum", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_system", sa.String(length=80), nullable=True),
        sa.Column("deviation_details", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["device_configuration_id"], ["program_device_configuration.id"]
        ),
        sa.ForeignKeyConstraint(["production_stage_run_id"], ["production_stage_run.id"]),
        sa.ForeignKeyConstraint(["trajectory_program_id"], ["trajectory_program.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_stage_run_id", name="uq_stage_device_execution"),
    )
    op.create_table(
        "path_segment_execution",
        sa.Column("device_execution_id", sa.String(length=36), nullable=False),
        sa.Column("path_segment_id", sa.String(length=36), nullable=False),
        sa.Column("actual_speed", sa.Float(), nullable=True),
        sa.Column("speed_unit", sa.String(length=24), nullable=True),
        sa.Column("trigger_state", sa.String(length=24), nullable=True),
        sa.Column("actual_values", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["device_execution_id"], ["production_device_execution.id"]),
        sa.ForeignKeyConstraint(["path_segment_id"], ["trajectory_path_segment.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_execution_id",
            "path_segment_id",
            name="uq_device_path_segment_execution",
        ),
    )
    op.create_index(
        "ix_point_feature_snapshot_production_run_id",
        "point_feature_snapshot",
        ["production_run_id"],
    )
    op.create_index(
        "ix_point_feature_snapshot_measurement_point_id",
        "point_feature_snapshot",
        ["measurement_point_id"],
    )
    with op.batch_alter_table("point_feature_snapshot") as batch_op:
        batch_op.drop_constraint("uq_run_point_feature_version", type_="unique")
        batch_op.add_column(
            sa.Column(
                "target_family",
                sa.String(length=32),
                server_default="ORANGE_PEEL",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("lineage", sa.JSON(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_run_point_feature_target_version",
            [
                "production_run_id",
                "measurement_point_id",
                "feature_set_version",
                "target_family",
            ],
        )
    op.execute("UPDATE point_feature_snapshot SET lineage = JSON_OBJECT() WHERE lineage IS NULL")
    with op.batch_alter_table("point_feature_snapshot") as batch_op:
        batch_op.alter_column("lineage", existing_type=sa.JSON(), nullable=False)

    # Feature semantics now require target-family contribution and trajectory lineage.
    op.execute("UPDATE model_version SET status = 'RETIRED' WHERE status = 'ACTIVE'")


def downgrade() -> None:
    with op.batch_alter_table("point_feature_snapshot") as batch_op:
        batch_op.drop_constraint("uq_run_point_feature_target_version", type_="unique")
        batch_op.drop_column("lineage")
        batch_op.drop_column("target_family")
        batch_op.create_unique_constraint(
            "uq_run_point_feature_version",
            ["production_run_id", "measurement_point_id", "feature_set_version"],
        )
    op.drop_index(
        "ix_point_feature_snapshot_measurement_point_id",
        table_name="point_feature_snapshot",
    )
    op.drop_index(
        "ix_point_feature_snapshot_production_run_id",
        table_name="point_feature_snapshot",
    )
    op.drop_table("path_segment_execution")
    op.drop_table("production_device_execution")
    op.drop_table("point_contribution_entry")
    op.drop_table("point_contribution_version")
    op.drop_table("trajectory_path_segment")
    op.drop_table("trajectory_program")
    op.drop_table("program_device_configuration")
    op.drop_table("durr_rotary_atomizer")
    op.drop_table("durr_application_controller")
    op.drop_table("durr_robot")
