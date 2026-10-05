"""Lucky draw profile photo and whether the ticket is in a day's pool.

Revision ID: m9n0p1q2r3s4
Revises: l8m9n0p1q2r3
Create Date: 2026-10-02 14:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, drop_column_if_exists, table_exists


revision: str = "m9n0p1q2r3s4"
down_revision: Union[str, None] = "l8m9n0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not table_exists("event_lucky_entries"):
        return
    add_column_if_missing("event_lucky_entries", sa.Column("photo_url", sa.String(400), nullable=True))
    add_column_if_missing(
        "event_lucky_entries",
        sa.Column("draw_eligible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    if not table_exists("event_lucky_entries"):
        return
    drop_column_if_exists("event_lucky_entries", "draw_eligible")
    drop_column_if_exists("event_lucky_entries", "photo_url")
