"""Backfill industrial_visits.is_deleted NULL -> false

Revision ID: y1z2a3b4c5d6
Revises: x0y1z2a3b4c5
Create Date: 2026-11-04 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "y1z2a3b4c5d6"
down_revision: Union[str, None] = "x0y1z2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE industrial_visits SET is_deleted = false WHERE is_deleted IS NULL"
    )
    op.alter_column(
        "industrial_visits",
        "is_deleted",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_industrial_visits_is_deleted "
        "ON industrial_visits (is_deleted)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_industrial_visits_is_deleted")
    op.alter_column(
        "industrial_visits",
        "is_deleted",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )
