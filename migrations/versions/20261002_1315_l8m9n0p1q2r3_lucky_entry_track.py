"""Store lucky-draw stream and a longer location string.

Revision ID: l8m9n0p1q2r3
Revises: k7l8m9n0p1q2
Create Date: 2026-10-02 13:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l8m9n0p1q2r3"
down_revision: Union[str, None] = "k7l8m9n0p1q2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("event_lucky_entries"):
        return
    cols = {col["name"]: col for col in inspector.get_columns("event_lucky_entries")}
    if "track" not in cols:
        op.add_column("event_lucky_entries", sa.Column("track", sa.String(20), nullable=True))
    location = cols.get("location")
    if location is not None:
        op.alter_column("event_lucky_entries", "location", type_=sa.String(250), existing_nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("event_lucky_entries"):
        return
    cols = {col["name"] for col in inspector.get_columns("event_lucky_entries")}
    if "track" in cols:
        op.drop_column("event_lucky_entries", "track")
    op.alter_column("event_lucky_entries", "location", type_=sa.String(150), existing_nullable=True)
