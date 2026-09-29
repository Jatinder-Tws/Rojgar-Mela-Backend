"""Expand site_announcements for events, modals, slider banners, and expiry.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-29 17:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen text column to Text
    op.alter_column("site_announcements", "text", type_=sa.Text(), existing_nullable=False)
    
    op.add_column("site_announcements", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("site_announcements", sa.Column("category", sa.String(length=50), nullable=False, server_default="announcement"))
    op.add_column("site_announcements", sa.Column("display_placement", sa.String(length=50), nullable=False, server_default="top_banner"))
    op.add_column("site_announcements", sa.Column("target_pages", sa.String(length=255), nullable=False, server_default="all"))
    op.add_column("site_announcements", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("site_announcements", sa.Column("link_text", sa.String(length=100), nullable=True))
    op.add_column("site_announcements", sa.Column("event_date", sa.DateTime(), nullable=True))
    op.add_column("site_announcements", sa.Column("event_location", sa.String(length=255), nullable=True))
    op.add_column("site_announcements", sa.Column("organizer", sa.String(length=255), nullable=True))
    op.add_column("site_announcements", sa.Column("modal_delay_seconds", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("site_announcements", sa.Column("start_date", sa.DateTime(), nullable=True))
    op.add_column("site_announcements", sa.Column("expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("site_announcements", "expires_at")
    op.drop_column("site_announcements", "start_date")
    op.drop_column("site_announcements", "modal_delay_seconds")
    op.drop_column("site_announcements", "organizer")
    op.drop_column("site_announcements", "event_location")
    op.drop_column("site_announcements", "event_date")
    op.drop_column("site_announcements", "link_text")
    op.drop_column("site_announcements", "image_url")
    op.drop_column("site_announcements", "target_pages")
    op.drop_column("site_announcements", "display_placement")
    op.drop_column("site_announcements", "category")
    op.drop_column("site_announcements", "title")
