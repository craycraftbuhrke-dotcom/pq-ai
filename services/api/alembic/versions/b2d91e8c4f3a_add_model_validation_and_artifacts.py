"""add model validation folds and artifacts

Revision ID: b2d91e8c4f3a
Revises: a4c91e2b7d60
Create Date: 2026-06-15 15:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b2d91e8c4f3a"
down_revision: str | None = "a4c91e2b7d60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_validation_fold",
        sa.Column("model_version_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("validation_axis", sa.String(length=48), nullable=False),
        sa.Column("fold_key", sa.String(length=120), nullable=False),
        sa.Column("train_sample_count", sa.Integer(), nullable=False),
        sa.Column("validation_sample_count", sa.Integer(), nullable=False),
        sa.Column("train_group_count", sa.Integer(), nullable=False),
        sa.Column("validation_group_count", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["dataset_snapshot_id"], ["dataset_snapshot.id"]),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_version.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_version_id",
            "validation_axis",
            "fold_key",
            name="uq_model_validation_fold",
        ),
    )
    op.create_index(
        "ix_model_validation_axis",
        "model_validation_fold",
        ["model_version_id", "validation_axis", "status"],
    )
    op.create_table(
        "model_artifact",
        sa.Column("model_version_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_type", sa.String(length=48), nullable=False),
        sa.Column("artifact_uri", sa.String(length=500), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["model_version_id"], ["model_version.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_version_id",
            "artifact_type",
            name="uq_model_artifact_type",
        ),
    )
    op.create_index(
        "ix_model_artifact_status",
        "model_artifact",
        ["model_version_id", "status"],
    )
    op.execute("UPDATE model_version SET status = 'RETIRED' WHERE status = 'ACTIVE'")


def downgrade() -> None:
    op.drop_index("ix_model_artifact_status", table_name="model_artifact")
    op.drop_table("model_artifact")
    op.drop_index("ix_model_validation_axis", table_name="model_validation_fold")
    op.drop_table("model_validation_fold")
