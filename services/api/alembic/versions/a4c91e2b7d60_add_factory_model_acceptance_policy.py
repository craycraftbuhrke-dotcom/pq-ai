"""add factory model acceptance policy

Revision ID: a4c91e2b7d60
Revises: f0a7b4c82d19
Create Date: 2026-06-15 13:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a4c91e2b7d60"
down_revision: str | None = "f0a7b4c82d19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_acceptance_policy",
        sa.Column("policy_code", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("factory_id", sa.String(length=36), nullable=False),
        sa.Column("target_metric", sa.String(length=64), nullable=False),
        sa.Column("policy_type", sa.String(length=24), nullable=False),
        sa.Column("max_validation_rmse", sa.Float(), nullable=False),
        sa.Column("min_validation_r2", sa.Float(), nullable=False),
        sa.Column("min_train_groups", sa.Integer(), nullable=False),
        sa.Column("min_validation_groups", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=False),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["factory_id"], ["factory.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_code",
            "version",
            name="uq_model_acceptance_policy_version",
        ),
    )
    op.create_index(
        "ix_model_acceptance_policy_match",
        "model_acceptance_policy",
        ["factory_id", "target_metric", "status"],
    )
    op.execute("UPDATE model_version SET status = 'RETIRED' WHERE status = 'ACTIVE'")


def downgrade() -> None:
    op.drop_index("ix_model_acceptance_policy_match", table_name="model_acceptance_policy")
    op.drop_table("model_acceptance_policy")
