"""Align existing event_lucky_entries table with the lucky-draw model.

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-10-01 13:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from migrations.helpers import (
    add_column_if_missing,
    column_names,
    create_index_if_missing,
    drop_column_if_exists,
    drop_index_if_exists,
    execute_if_columns,
    table_exists,
)


revision: str = "i5j6k7l8m9n0"
down_revision: Union[str, None] = "h4i5j6k7l8m9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not table_exists("event_lucky_entries"):
        return

    add_column_if_missing("event_lucky_entries", sa.Column("location", sa.String(150), nullable=True))
    add_column_if_missing("event_lucky_entries", sa.Column("organization", sa.String(200), nullable=True))
    add_column_if_missing("event_lucky_entries", sa.Column("draw_date", sa.String(10), nullable=True))
    add_column_if_missing(
        "event_lucky_entries",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    add_column_if_missing(
        "event_lucky_entries",
        sa.Column("is_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    add_column_if_missing("event_lucky_entries", sa.Column("verified_at", sa.DateTime(), nullable=True))
    add_column_if_missing(
        "event_lucky_entries",
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    cols = column_names("event_lucky_entries")

    if "draw_date" in cols and "created_at" in cols:
        op.execute(
            "UPDATE event_lucky_entries SET draw_date = to_char(created_at, 'YYYY-MM-DD') WHERE draw_date IS NULL"
        )

    # Legacy tables only — status does not exist on the current model.
    execute_if_columns(
        "event_lucky_entries",
        ("status", "email_verified"),
        "UPDATE event_lucky_entries SET email_verified = true "
        "WHERE status = 'verified' AND email_verified IS false",
    )

    if "draw_date" in cols:
        op.execute(
            "UPDATE event_lucky_entries SET draw_date = to_char(now(), 'YYYY-MM-DD') WHERE draw_date IS NULL"
        )
        op.alter_column("event_lucky_entries", "draw_date", existing_type=sa.String(10), nullable=False)

    if "updated_at" in cols:
        op.execute("ALTER TABLE event_lucky_entries ALTER COLUMN updated_at SET DEFAULT now()")

    op.execute("ALTER TABLE event_lucky_entries DROP CONSTRAINT IF EXISTS uq_event_lucky_entry_email")
    create_index_if_missing("ix_event_lucky_entries_draw_date", "event_lucky_entries", ["draw_date"])


def downgrade() -> None:
    drop_index_if_exists("ix_event_lucky_entries_draw_date", "event_lucky_entries")
    drop_column_if_exists("event_lucky_entries", "verified_at")
    drop_column_if_exists("event_lucky_entries", "is_winner")
    drop_column_if_exists("event_lucky_entries", "email_verified")
    drop_column_if_exists("event_lucky_entries", "draw_date")
    drop_column_if_exists("event_lucky_entries", "organization")
    drop_column_if_exists("event_lucky_entries", "location")
