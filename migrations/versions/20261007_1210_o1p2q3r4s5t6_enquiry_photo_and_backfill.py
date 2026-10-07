"""Add career enquiry photo_url and backfill from lucky entries / users.

Revision ID: o1p2q3r4s5t6
Revises: n0p1q2r3s4t5
Create Date: 2026-10-07 12:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing, drop_column_if_exists, table_exists


revision: str = "o1p2q3r4s5t6"
down_revision: Union[str, None] = "n0p1q2r3s4t5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if table_exists("career_enquiries"):
        add_column_if_missing(
            "career_enquiries",
            sa.Column("photo_url", sa.String(400), nullable=True),
        )

    conn = op.get_bind()

    # Copy lucky-draw photos onto matching enquiries (by enquiry_id, then ticket).
    if table_exists("career_enquiries") and table_exists("event_lucky_entries"):
        conn.execute(
            sa.text(
                """
                UPDATE career_enquiries ce
                SET photo_url = ele.photo_url
                FROM event_lucky_entries ele
                WHERE ce.photo_url IS NULL
                  AND ele.photo_url IS NOT NULL
                  AND ele.enquiry_id IS NOT NULL
                  AND ele.enquiry_id::text = ce.id::text
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE career_enquiries ce
                SET photo_url = ele.photo_url
                FROM event_lucky_entries ele
                WHERE ce.photo_url IS NULL
                  AND ele.photo_url IS NOT NULL
                  AND ele.ticket_number IS NOT NULL
                  AND ce.ticket_number IS NOT NULL
                  AND ele.ticket_number = ce.ticket_number
                """
            )
        )

    # Sync lucky photos onto seeker accounts that still have no profile pic.
    if table_exists("users") and table_exists("event_lucky_entries"):
        conn.execute(
            sa.text(
                """
                UPDATE users u
                SET profile_pic_url = ele.photo_url
                FROM event_lucky_entries ele
                WHERE (u.profile_pic_url IS NULL OR btrim(u.profile_pic_url) = '')
                  AND ele.photo_url IS NOT NULL
                  AND ele.email_verified IS TRUE
                  AND lower(u.email) = lower(ele.email)
                """
            )
        )


def downgrade() -> None:
    if table_exists("career_enquiries"):
        drop_column_if_exists("career_enquiries", "photo_url")
