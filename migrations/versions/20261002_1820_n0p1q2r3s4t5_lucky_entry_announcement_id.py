"""Use announcement_id on lucky draw entries when the table still has event_id.

Revision ID: n0p1q2r3s4t5
Revises: m9n0p1q2r3s4
Create Date: 2026-10-02 18:20:00.000000
"""
from typing import Sequence, Union

from alembic import op

from migrations.helpers import column_names, table_exists


revision: str = "n0p1q2r3s4t5"
down_revision: Union[str, None] = "m9n0p1q2r3s4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not table_exists("event_lucky_entries"):
        return
    cols = column_names("event_lucky_entries")
    if "event_id" in cols and "announcement_id" not in cols:
        op.alter_column("event_lucky_entries", "event_id", new_column_name="announcement_id")


def downgrade() -> None:
    if not table_exists("event_lucky_entries"):
        return
    cols = column_names("event_lucky_entries")
    if "announcement_id" in cols and "event_id" not in cols:
        op.alter_column("event_lucky_entries", "announcement_id", new_column_name="event_id")
