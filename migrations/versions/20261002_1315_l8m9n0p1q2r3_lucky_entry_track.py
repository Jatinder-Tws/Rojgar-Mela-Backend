"""Store lucky-draw stream and a longer location string.

Revision ID: l8m9n0p1q2r3
Revises: k7l8m9n0p1q2
Create Date: 2026-10-02 13:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, column_names, drop_column_if_exists, table_exists


revision: str = "l8m9n0p1q2r3"
down_revision: Union[str, None] = "k7l8m9n0p1q2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not table_exists("event_lucky_entries"):
        return
    add_column_if_missing("event_lucky_entries", sa.Column("track", sa.String(20), nullable=True))
    if "location" in column_names("event_lucky_entries"):
        op.alter_column("event_lucky_entries", "location", type_=sa.String(250), existing_nullable=True)


def downgrade() -> None:
    if not table_exists("event_lucky_entries"):
        return
    drop_column_if_exists("event_lucky_entries", "track")
    if "location" in column_names("event_lucky_entries"):
        op.alter_column("event_lucky_entries", "location", type_=sa.String(150), existing_nullable=True)
