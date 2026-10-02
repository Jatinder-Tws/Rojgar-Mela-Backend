"""Align existing event_lucky_entries table with the lucky-draw model.

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-10-01 13:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i5j6k7l8m9n0"
down_revision: Union[str, None] = "h4i5j6k7l8m9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("event_lucky_entries"):
        return

    cols = {col["name"] for col in inspector.get_columns("event_lucky_entries")}

    if "location" not in cols:
        op.add_column("event_lucky_entries", sa.Column("location", sa.String(150), nullable=True))
    if "organization" not in cols:
        op.add_column("event_lucky_entries", sa.Column("organization", sa.String(200), nullable=True))
    if "draw_date" not in cols:
        op.add_column("event_lucky_entries", sa.Column("draw_date", sa.String(10), nullable=True))
    if "email_verified" not in cols:
        op.add_column(
            "event_lucky_entries",
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "is_winner" not in cols:
        op.add_column(
            "event_lucky_entries",
            sa.Column("is_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "verified_at" not in cols:
        op.add_column("event_lucky_entries", sa.Column("verified_at", sa.DateTime(), nullable=True))

    op.execute("UPDATE event_lucky_entries SET draw_date = to_char(created_at, 'YYYY-MM-DD') WHERE draw_date IS NULL")
    op.execute("UPDATE event_lucky_entries SET email_verified = true WHERE status = 'verified' AND email_verified IS false")
    op.alter_column("event_lucky_entries", "draw_date", existing_type=sa.String(10), nullable=False)
    op.execute("ALTER TABLE event_lucky_entries ALTER COLUMN updated_at SET DEFAULT now()")

    op.execute("ALTER TABLE event_lucky_entries DROP CONSTRAINT IF EXISTS uq_event_lucky_entry_email")
    indexes = {idx["name"] for idx in inspector.get_indexes("event_lucky_entries")}
    if "ix_event_lucky_entries_draw_date" not in indexes:
        op.create_index("ix_event_lucky_entries_draw_date", "event_lucky_entries", ["draw_date"])


def downgrade() -> None:
    op.drop_index("ix_event_lucky_entries_draw_date", table_name="event_lucky_entries")
    op.drop_column("event_lucky_entries", "verified_at")
    op.drop_column("event_lucky_entries", "is_winner")
    op.drop_column("event_lucky_entries", "email_verified")
    op.drop_column("event_lucky_entries", "draw_date")
    op.drop_column("event_lucky_entries", "organization")
    op.drop_column("event_lucky_entries", "location")
