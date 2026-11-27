"""Add collected_date column to training_portal_transactions table.

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-11-27 11:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, drop_column_if_exists

revision: str = "j2k3l4m5n6o7"
down_revision: Union[str, None] = "i1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "training_portal_transactions",
        sa.Column("collected_date", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    drop_column_if_exists("training_portal_transactions", "collected_date")
