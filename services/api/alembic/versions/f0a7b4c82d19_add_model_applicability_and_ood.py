"""add model applicability and ood governance

Revision ID: f0a7b4c82d19
Revises: e3a6c9d21f70
Create Date: 2026-06-15 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f0a7b4c82d19"
down_revision: str | None = "e3a6c9d21f70"
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
        "model_applicability_scope",
        sa.Column("model_version_id", sa.String(length=36), nullable=False),
        sa.Column("factory_id", sa.String(length=36), nullable=False),
        sa.Column("vehicle_model_id", sa.String(length=36), nullable=False),
        sa.Column("color_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["color_id"], ["color.id"]),
        sa.ForeignKeyConstraint(["factory_id"], ["factory.id"]),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_version.id"]),
        sa.ForeignKeyConstraint(["vehicle_model_id"], ["vehicle_model.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_version_id",
            "factory_id",
            "vehicle_model_id",
            "color_id",
            name="uq_model_applicability_context",
        ),
    )
    op.create_index(
        "ix_model_applicability_status",
        "model_applicability_scope",
        ["model_version_id", "status"],
    )
    op.create_table(
        "model_ood_policy",
        sa.Column("model_version_id", sa.String(length=36), nullable=False),
        sa.Column("max_abs_standardized_shift", sa.Float(), nullable=False),
        sa.Column("max_outlier_feature_ratio", sa.Float(), nullable=False),
        sa.Column("min_feature_completeness", sa.Float(), nullable=False),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_version.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_version_id", name="uq_model_ood_policy_version"),
    )
    op.add_column(
        "prediction_result",
        sa.Column(
            "applicability_status",
            sa.String(length=24),
            server_default="LEGACY_UNGOVERNED",
            nullable=False,
        ),
    )
    op.add_column(
        "prediction_result",
        sa.Column(
            "ood_status",
            sa.String(length=24),
            server_default="LEGACY_UNGOVERNED",
            nullable=False,
        ),
    )
    op.add_column(
        "prediction_result",
        sa.Column("governance_evidence", sa.JSON(), nullable=True),
    )
    op.execute("UPDATE model_version SET status = 'RETIRED' WHERE status = 'ACTIVE'")


def downgrade() -> None:
    op.drop_column("prediction_result", "governance_evidence")
    op.drop_column("prediction_result", "ood_status")
    op.drop_column("prediction_result", "applicability_status")
    op.drop_table("model_ood_policy")
    op.drop_index("ix_model_applicability_status", table_name="model_applicability_scope")
    op.drop_table("model_applicability_scope")
