"""Lucky draw profile photo and whether the ticket is in a day's pool.

Revision ID: m9n0p1q2r3s4
Revises: l8m9n0p1q2r3
Create Date: 2026-10-02 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m9n0p1q2r3s4"
down_revision: Union[str, None] = "l8m9n0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("event_lucky_entries"):
        return
    cols = {col["name"] for col in inspector.get_columns("event_lucky_entries")}
    if "photo_url" not in cols:
        op.add_column("event_lucky_entries", sa.Column("photo_url", sa.String(400), nullable=True))
    if "draw_eligible" not in cols:
        op.add_column(
            "event_lucky_entries",
            sa.Column("draw_eligible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("event_lucky_entries"):
        return
    cols = {col["name"] for col in inspector.get_columns("event_lucky_entries")}
    if "draw_eligible" in cols:
        op.drop_column("event_lucky_entries", "draw_eligible")
    if "photo_url" in cols:
        op.drop_column("event_lucky_entries", "photo_url")
