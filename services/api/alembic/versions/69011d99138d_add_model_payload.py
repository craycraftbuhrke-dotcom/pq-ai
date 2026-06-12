"""add_model_payload

Revision ID: 69011d99138d
Revises: f615aa57c04b
Create Date: 2026-06-10 08:26:59.637242
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '69011d99138d'
down_revision: str | None = 'f615aa57c04b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('model_version', sa.Column('model_payload', sa.JSON(), nullable=True))
    op.add_column('model_version', sa.Column('training_sample_count', sa.Integer(), nullable=True))
    op.add_column('model_version', sa.Column('trained_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE model_version SET model_payload = '{}' WHERE model_payload IS NULL")
    op.execute(
        "UPDATE model_version SET training_sample_count = 0 WHERE training_sample_count IS NULL"
    )
    with op.batch_alter_table('model_version') as batch_op:
        batch_op.alter_column(
            'model_payload',
            existing_type=sa.JSON(),
            nullable=False,
        )
        batch_op.alter_column(
            'training_sample_count',
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    op.drop_column('model_version', 'trained_at')
    op.drop_column('model_version', 'training_sample_count')
    op.drop_column('model_version', 'model_payload')
