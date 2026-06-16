"""add constraint sources and rollbacks

Revision ID: d4f8a9c2b7e3
Revises: c7a5d2e4b6f1
Create Date: 2026-06-16 10:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a9c2b7e3"
down_revision: str | None = "c7a5d2e4b6f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parameter_constraint_source",
        sa.Column("parameter_definition_id", sa.String(length=36), nullable=False),
        sa.Column("factory_id", sa.String(length=36), nullable=True),
        sa.Column("process_stage", sa.String(length=32), nullable=True),
        sa.Column("constraint_code", sa.String(length=96), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=True),
        sa.Column("lower_limit", sa.Float(), nullable=False),
        sa.Column("upper_limit", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["factory_id"], ["factory.id"], name="fk_constraint_source_factory"
        ),
        sa.ForeignKeyConstraint(
            ["parameter_definition_id"],
            ["parameter_definition.id"],
            name="fk_constraint_source_parameter_definition",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "constraint_code", name="uq_parameter_constraint_source_code"
        ),
    )
    op.create_index(
        "ix_parameter_constraint_lookup",
        "parameter_constraint_source",
        ["parameter_definition_id", "factory_id", "process_stage", "status"],
    )
    op.add_column(
        "recommendation_action",
        sa.Column("constraint_source_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "recommendation_action",
        sa.Column("constraint_source_code", sa.String(length=96), nullable=True),
    )
    op.add_column(
        "recommendation_action",
        sa.Column("constraint_source_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "recommendation_action",
        sa.Column("constraint_source_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "recommendation_action",
        sa.Column("constraint_source_uri", sa.String(length=500), nullable=True),
    )
    op.create_foreign_key(
        "fk_recommendation_action_constraint_source",
        "recommendation_action",
        "parameter_constraint_source",
        ["constraint_source_id"],
        ["id"],
    )
    op.create_table(
        "program_rollback_execution",
        sa.Column("rollback_no", sa.String(length=64), nullable=False),
        sa.Column("recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("controlled_trial_id", sa.String(length=36), nullable=False),
        sa.Column("rollback_to_program_version_id", sa.String(length=36), nullable=True),
        sa.Column("rollback_reason", sa.Text(), nullable=False),
        sa.Column("execution_note", sa.Text(), nullable=True),
        sa.Column("executed_by", sa.String(length=80), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("action_snapshot", sa.JSON(), nullable=False),
        sa.Column("verified_by", sa.String(length=80), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_comment", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["controlled_trial_id"],
            ["controlled_trial.id"],
            name="fk_rollback_controlled_trial",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"], ["recommendation.id"], name="fk_rollback_recommendation"
        ),
        sa.ForeignKeyConstraint(
            ["rollback_to_program_version_id"],
            ["spray_program_version.id"],
            name="fk_rollback_program_version",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("controlled_trial_id", name="uq_rollback_controlled_trial"),
        sa.UniqueConstraint("rollback_no", name="uq_program_rollback_no"),
    )
    op.create_index(
        "ix_program_rollback_status",
        "program_rollback_execution",
        ["status", "executed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_program_rollback_status", table_name="program_rollback_execution")
    op.drop_table("program_rollback_execution")
    op.drop_constraint(
        "fk_recommendation_action_constraint_source",
        "recommendation_action",
        type_="foreignkey",
    )
    op.drop_column("recommendation_action", "constraint_source_uri")
    op.drop_column("recommendation_action", "constraint_source_type")
    op.drop_column("recommendation_action", "constraint_source_version")
    op.drop_column("recommendation_action", "constraint_source_code")
    op.drop_column("recommendation_action", "constraint_source_id")
    op.drop_index("ix_parameter_constraint_lookup", table_name="parameter_constraint_source")
    op.drop_table("parameter_constraint_source")
