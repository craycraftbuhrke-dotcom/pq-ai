"""add leakage safe model governance

Revision ID: e3a6c9d21f70
Revises: d5e7a2c91f04
Create Date: 2026-06-15 09:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e3a6c9d21f70"
down_revision: str | None = "d5e7a2c91f04"
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
        "dataset_snapshot",
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("target_metric", sa.String(length=64), nullable=False),
        sa.Column("feature_set_version", sa.String(length=64), nullable=False),
        sa.Column("split_strategy", sa.String(length=48), nullable=False),
        sa.Column("group_key", sa.String(length=32), nullable=False),
        sa.Column("holdout_ratio", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("group_count", sa.Integer(), nullable=False),
        sa.Column("train_sample_count", sa.Integer(), nullable=False),
        sa.Column("validation_sample_count", sa.Integer(), nullable=False),
        sa.Column("train_group_count", sa.Integer(), nullable=False),
        sa.Column("validation_group_count", sa.Integer(), nullable=False),
        sa.Column("cutoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("feature_names", sa.JSON(), nullable=False),
        sa.Column("lineage", sa.JSON(), nullable=False),
        sa.Column("leakage_check", sa.JSON(), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_code", "version", name="uq_dataset_snapshot_version"),
    )
    op.create_table(
        "dataset_split_member",
        sa.Column("dataset_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("point_feature_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("production_run_id", sa.String(length=36), nullable=False),
        sa.Column("measurement_point_id", sa.String(length=36), nullable=False),
        sa.Column("target_measurement_id", sa.String(length=36), nullable=False),
        sa.Column("group_value", sa.String(length=100), nullable=False),
        sa.Column("split", sa.String(length=24), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("feature_values", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["dataset_snapshot_id"], ["dataset_snapshot.id"]),
        sa.ForeignKeyConstraint(["point_feature_snapshot_id"], ["point_feature_snapshot.id"]),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_run.id"]),
        sa.ForeignKeyConstraint(["measurement_point_id"], ["measurement_point.id"]),
        sa.ForeignKeyConstraint(["target_measurement_id"], ["quality_measurement.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_snapshot_id",
            "point_feature_snapshot_id",
            name="uq_dataset_feature_snapshot",
        ),
    )
    op.create_index(
        "ix_dataset_split_group",
        "dataset_split_member",
        ["dataset_snapshot_id", "split", "group_value"],
    )
    op.add_column(
        "model_version",
        sa.Column("dataset_snapshot_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_model_version_dataset_snapshot",
        "model_version",
        "dataset_snapshot",
        ["dataset_snapshot_id"],
        ["id"],
    )
    op.create_table(
        "model_acceptance_decision",
        sa.Column("model_version_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("decided_by", sa.String(length=80), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["dataset_snapshot_id"], ["dataset_snapshot.id"]),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_version.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_acceptance_decision_time",
        "model_acceptance_decision",
        ["model_version_id", "decided_at"],
    )
    op.execute("UPDATE model_version SET status = 'RETIRED' WHERE status = 'ACTIVE'")


def downgrade() -> None:
    op.drop_index(
        "ix_model_acceptance_decision_time",
        table_name="model_acceptance_decision",
    )
    op.drop_table("model_acceptance_decision")
    op.drop_constraint("fk_model_version_dataset_snapshot", "model_version", type_="foreignkey")
    op.drop_column("model_version", "dataset_snapshot_id")
    op.drop_index("ix_dataset_split_group", table_name="dataset_split_member")
    op.drop_table("dataset_split_member")
    op.drop_table("dataset_snapshot")
