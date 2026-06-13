"""add governed material characteristics

Revision ID: d5e7a2c91f04
Revises: c34f9a0d2e18
Create Date: 2026-06-13 16:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d5e7a2c91f04"
down_revision: str | None = "c34f9a0d2e18"
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
        "material_characteristic_definition",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("canonical_unit", sa.String(length=24), nullable=False),
        sa.Column("target_families", sa.JSON(), nullable=False),
        sa.Column("is_model_feature", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "material_test_method",
        sa.Column("characteristic_definition_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("method_type", sa.String(length=64), nullable=False),
        sa.Column("result_unit", sa.String(length=24), nullable=False),
        sa.Column("procedure_uri", sa.String(length=500), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["characteristic_definition_id"], ["material_characteristic_definition.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_material_test_method_version"),
    )
    op.create_table(
        "material_specification",
        sa.Column("material_code", sa.String(length=64), nullable=False),
        sa.Column("characteristic_definition_id", sa.String(length=36), nullable=False),
        sa.Column("method_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("lower_limit", sa.Float(), nullable=True),
        sa.Column("upper_limit", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_uri", sa.String(length=500), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["characteristic_definition_id"], ["material_characteristic_definition.id"]
        ),
        sa.ForeignKeyConstraint(["method_id"], ["material_test_method.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_code",
            "characteristic_definition_id",
            "method_id",
            "version",
            name="uq_material_specification_version",
        ),
    )
    op.create_table(
        "material_characteristic_applicability",
        sa.Column("characteristic_definition_id", sa.String(length=36), nullable=False),
        sa.Column("material_type", sa.String(length=24), nullable=False),
        sa.Column("process_stage", sa.String(length=32), nullable=False),
        sa.Column("target_family", sa.String(length=32), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("approved_by", sa.String(length=80), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["characteristic_definition_id"], ["material_characteristic_definition.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "characteristic_definition_id",
            "material_type",
            "process_stage",
            "target_family",
            name="uq_material_characteristic_applicability",
        ),
    )
    op.create_table(
        "material_batch_test_result",
        sa.Column("result_no", sa.String(length=80), nullable=False),
        sa.Column("material_batch_id", sa.String(length=36), nullable=False),
        sa.Column("characteristic_definition_id", sa.String(length=36), nullable=False),
        sa.Column("method_id", sa.String(length=36), nullable=False),
        sa.Column("specification_id", sa.String(length=36), nullable=True),
        sa.Column("result_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tested_by", sa.String(length=80), nullable=True),
        sa.Column("source_uri", sa.String(length=500), nullable=True),
        sa.Column("raw_values", sa.JSON(), nullable=True),
        sa.Column("reliability_status", sa.String(length=24), nullable=False),
        sa.Column("reliability_issues", sa.JSON(), nullable=True),
        sa.Column("is_within_spec", sa.Boolean(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["material_batch_id"], ["material_batch.id"]),
        sa.ForeignKeyConstraint(
            ["characteristic_definition_id"], ["material_characteristic_definition.id"]
        ),
        sa.ForeignKeyConstraint(["method_id"], ["material_test_method.id"]),
        sa.ForeignKeyConstraint(["specification_id"], ["material_specification.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("result_no"),
    )
    op.create_index(
        "ix_material_result_batch_characteristic_time",
        "material_batch_test_result",
        ["material_batch_id", "characteristic_definition_id", "tested_at"],
    )
    op.execute("UPDATE model_version SET status = 'RETIRED' WHERE status = 'ACTIVE'")


def downgrade() -> None:
    op.drop_index(
        "ix_material_result_batch_characteristic_time",
        table_name="material_batch_test_result",
    )
    op.drop_table("material_batch_test_result")
    op.drop_table("material_characteristic_applicability")
    op.drop_table("material_specification")
    op.drop_table("material_test_method")
    op.drop_table("material_characteristic_definition")
