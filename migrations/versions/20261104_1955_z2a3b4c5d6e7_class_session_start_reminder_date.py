"""Add start_reminder_for_date to class sessions (day-scoped 30/15 reminders).

Revision ID: z2a3b4c5d6e7
Revises: y1z2a3b4c5d6
Create Date: 2026-11-04 19:55:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing, drop_column_if_exists

revision: str = "z2a3b4c5d6e7"
down_revision: Union[str, None] = "y1z2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "training_portal_class_sessions",
        sa.Column("start_reminder_for_date", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    drop_column_if_exists("training_portal_class_sessions", "start_reminder_for_date")
