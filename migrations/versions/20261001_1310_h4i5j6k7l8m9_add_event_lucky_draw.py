"""Lucky draw registrations on site events.

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-10-01 13:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "h4i5j6k7l8m9"
down_revision: Union[str, None] = "g3h4i5j6k7l8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    announcement_cols = {col["name"] for col in inspector.get_columns("site_announcements")}
    if "lucky_draw_enabled" not in announcement_cols:
        op.add_column("site_announcements", sa.Column("lucky_draw_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if "lucky_draw_slug" not in announcement_cols:
        op.add_column("site_announcements", sa.Column("lucky_draw_slug", sa.String(80), nullable=True))
    if "lucky_draw_days" not in announcement_cols:
        op.add_column("site_announcements", sa.Column("lucky_draw_days", sa.Integer(), nullable=False, server_default="1"))
    if "lucky_draw_reveal_time" not in announcement_cols:
        op.add_column("site_announcements", sa.Column("lucky_draw_reveal_time", sa.String(5), nullable=False, server_default="18:00"))
    indexes = {idx["name"] for idx in inspector.get_indexes("site_announcements")}
    if "ix_site_announcements_lucky_draw_slug" not in indexes:
        op.create_index("ix_site_announcements_lucky_draw_slug", "site_announcements", ["lucky_draw_slug"], unique=True)

    if not inspector.has_table("event_lucky_entries"):
        op.create_table(
            "event_lucky_entries",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("announcement_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("full_name", sa.String(150), nullable=False),
            sa.Column("email", sa.String(150), nullable=False),
            sa.Column("phone", sa.String(20), nullable=False),
            sa.Column("location", sa.String(150), nullable=True),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("organization", sa.String(200), nullable=True),
            sa.Column("ticket_number", sa.String(40), nullable=True),
            sa.Column("draw_date", sa.String(10), nullable=False),
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("enquiry_id", postgresql.UUID(as_uuid=False), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["announcement_id"], ["site_announcements.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("ticket_number", name="uq_event_lucky_ticket"),
        )
        op.create_index("ix_event_lucky_entries_announcement_id", "event_lucky_entries", ["announcement_id"])
        op.create_index("ix_event_lucky_entries_email", "event_lucky_entries", ["email"])
        op.create_index("ix_event_lucky_entries_draw_date", "event_lucky_entries", ["draw_date"])

    if not inspector.has_table("event_lucky_draws"):
        op.create_table(
            "event_lucky_draws",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("announcement_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("draw_date", sa.String(10), nullable=False),
            sa.Column("winner_entry_id", postgresql.UUID(as_uuid=False), nullable=True),
            sa.Column("revealed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["announcement_id"], ["site_announcements.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("announcement_id", "draw_date", name="uq_event_lucky_draw_day"),
        )
        op.create_index("ix_event_lucky_draws_announcement_id", "event_lucky_draws", ["announcement_id"])


def downgrade() -> None:
    op.drop_index("ix_event_lucky_draws_announcement_id", table_name="event_lucky_draws")
    op.drop_table("event_lucky_draws")
    op.drop_index("ix_event_lucky_entries_draw_date", table_name="event_lucky_entries")
    op.drop_index("ix_event_lucky_entries_email", table_name="event_lucky_entries")
    op.drop_index("ix_event_lucky_entries_announcement_id", table_name="event_lucky_entries")
    op.drop_table("event_lucky_entries")
    op.drop_index("ix_site_announcements_lucky_draw_slug", table_name="site_announcements")
    op.drop_column("site_announcements", "lucky_draw_reveal_time")
    op.drop_column("site_announcements", "lucky_draw_days")
    op.drop_column("site_announcements", "lucky_draw_slug")
    op.drop_column("site_announcements", "lucky_draw_enabled")
