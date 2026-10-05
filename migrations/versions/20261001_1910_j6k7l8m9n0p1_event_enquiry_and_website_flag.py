"""Event ticket fields on enquiries and website visibility for announcements.

Revision ID: j6k7l8m9n0p1
Revises: i5j6k7l8m9n0
Create Date: 2026-10-01 19:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from migrations.helpers import (
    add_column_if_missing,
    create_index_if_missing,
    drop_column_if_exists,
    drop_index_if_exists,
    first_existing_column,
    table_exists,
)
from alembic import op


revision: str = "j6k7l8m9n0p1"
down_revision: Union[str, None] = "i5j6k7l8m9n0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "site_announcements",
        sa.Column("show_on_website", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    add_column_if_missing("career_enquiries", sa.Column("ticket_number", sa.String(40), nullable=True))
    add_column_if_missing(
        "career_enquiries",
        sa.Column("is_event_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    add_column_if_missing(
        "career_enquiries",
        sa.Column("announcement_id", postgresql.UUID(as_uuid=False), nullable=True),
    )
    add_column_if_missing("career_enquiries", sa.Column("draw_date", sa.String(10), nullable=True))
    add_column_if_missing("career_enquiries", sa.Column("event_title", sa.String(200), nullable=True))
    create_index_if_missing(
        "ix_career_enquiries_announcement_id",
        "career_enquiries",
        ["announcement_id"],
    )

    if table_exists("event_lucky_entries"):
        # Fresh path uses announcement_id; older DBs still had event_id.
        announcement_col = first_existing_column(
            "event_lucky_entries",
            ("announcement_id", "event_id"),
        )
        if announcement_col:
            op.execute(
                f"""
                UPDATE career_enquiries AS ce
                SET ticket_number = ele.ticket_number,
                    announcement_id = ele.{announcement_col},
                    draw_date = ele.draw_date,
                    is_event_winner = COALESCE(ele.is_winner, false),
                    event_title = COALESCE(ce.event_title, ce.domain)
                FROM event_lucky_entries AS ele
                WHERE ele.enquiry_id IS NOT NULL
                  AND ele.enquiry_id::text = ce.id::text
                """
            )


def downgrade() -> None:
    drop_index_if_exists("ix_career_enquiries_announcement_id", "career_enquiries")
    drop_column_if_exists("career_enquiries", "event_title")
    drop_column_if_exists("career_enquiries", "draw_date")
    drop_column_if_exists("career_enquiries", "announcement_id")
    drop_column_if_exists("career_enquiries", "is_event_winner")
    drop_column_if_exists("career_enquiries", "ticket_number")
    drop_column_if_exists("site_announcements", "show_on_website")
