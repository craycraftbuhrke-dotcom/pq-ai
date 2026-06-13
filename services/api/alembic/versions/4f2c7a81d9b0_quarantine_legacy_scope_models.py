"""quarantine legacy scope models

Revision ID: 4f2c7a81d9b0
Revises: 9a40d2a88b91
Create Date: 2026-06-12 09:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "4f2c7a81d9b0"
down_revision: str | None = "9a40d2a88b91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # V1 snapshots may contain fields now excluded by the approved project scope.
    # Keep their data lineage, but prevent the associated models from remaining active.
    op.execute(
        "UPDATE model_version SET status = 'RETIRED' "
        "WHERE feature_set_version = 'point-features-v1'"
    )


def downgrade() -> None:
    # Unsafe legacy models are intentionally not reactivated on downgrade.
    pass
