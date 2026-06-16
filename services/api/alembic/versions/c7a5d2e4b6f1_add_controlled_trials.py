"""add controlled trials

Revision ID: c7a5d2e4b6f1
Revises: b2d91e8c4f3a
Create Date: 2026-06-16 09:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c7a5d2e4b6f1"
down_revision: str | None = "b2d91e8c4f3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "controlled_trial",
        sa.Column("recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("trial_no", sa.String(length=64), nullable=False),
        sa.Column("production_run_id", sa.String(length=36), nullable=False),
        sa.Column("measurement_point_id", sa.String(length=36), nullable=False),
        sa.Column("target_metric", sa.String(length=64), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("expected_outcome", sa.Text(), nullable=False),
        sa.Column("risk_assessment", sa.Text(), nullable=False),
        sa.Column("rollback_plan", sa.Text(), nullable=False),
        sa.Column("sustained_observation_plan", sa.Text(), nullable=False),
        sa.Column("constraint_evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("requested_by", sa.String(length=80), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_comment", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_summary", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["measurement_point_id"], ["measurement_point.id"]),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_run.id"]),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendation.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id", name="uq_controlled_trial_recommendation"),
        sa.UniqueConstraint("trial_no", name="uq_controlled_trial_no"),
    )
    op.create_index(
        "ix_controlled_trial_status",
        "controlled_trial",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_controlled_trial_status", table_name="controlled_trial")
    op.drop_table("controlled_trial")
