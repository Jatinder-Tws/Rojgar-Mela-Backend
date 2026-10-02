"""Event ticket fields on enquiries and website visibility for announcements.

Revision ID: j6k7l8m9n0p1
Revises: i5j6k7l8m9n0
Create Date: 2026-10-01 19:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "j6k7l8m9n0p1"
down_revision: Union[str, None] = "i5j6k7l8m9n0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    announcement_cols = {col["name"] for col in inspector.get_columns("site_announcements")}
    if "show_on_website" not in announcement_cols:
        op.add_column(
            "site_announcements",
            sa.Column("show_on_website", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )

    enquiry_cols = {col["name"] for col in inspector.get_columns("career_enquiries")}
    if "ticket_number" not in enquiry_cols:
        op.add_column("career_enquiries", sa.Column("ticket_number", sa.String(40), nullable=True))
    if "is_event_winner" not in enquiry_cols:
        op.add_column(
            "career_enquiries",
            sa.Column("is_event_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "announcement_id" not in enquiry_cols:
        op.add_column("career_enquiries", sa.Column("announcement_id", postgresql.UUID(as_uuid=False), nullable=True))
    if "draw_date" not in enquiry_cols:
        op.add_column("career_enquiries", sa.Column("draw_date", sa.String(10), nullable=True))
    if "event_title" not in enquiry_cols:
        op.add_column("career_enquiries", sa.Column("event_title", sa.String(200), nullable=True))
    indexes = {idx["name"] for idx in inspector.get_indexes("career_enquiries")}
    if "ix_career_enquiries_announcement_id" not in indexes:
        op.create_index("ix_career_enquiries_announcement_id", "career_enquiries", ["announcement_id"], unique=False)
    if "event_lucky_entries" in inspector.get_table_names():
        op.execute(
            """
            UPDATE career_enquiries AS ce
            SET ticket_number = ele.ticket_number,
                announcement_id = ele.event_id,
                draw_date = ele.draw_date,
                is_event_winner = COALESCE(ele.is_winner, false),
                event_title = COALESCE(ce.event_title, ce.domain)
            FROM event_lucky_entries AS ele
            WHERE ele.enquiry_id IS NOT NULL
              AND ele.enquiry_id::text = ce.id::text
            """
        )


def downgrade() -> None:
    op.drop_index("ix_career_enquiries_announcement_id", table_name="career_enquiries")
    op.drop_column("career_enquiries", "event_title")
    op.drop_column("career_enquiries", "draw_date")
    op.drop_column("career_enquiries", "announcement_id")
    op.drop_column("career_enquiries", "is_event_winner")
    op.drop_column("career_enquiries", "ticket_number")
    op.drop_column("site_announcements", "show_on_website")
