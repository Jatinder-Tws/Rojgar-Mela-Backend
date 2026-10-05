"""Expand site_announcements for events, modals, slider banners, and expiry.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-29 17:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, column_names, drop_column_if_exists


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = column_names("site_announcements")
    if "text" in cols:
        op.alter_column("site_announcements", "text", type_=sa.Text(), existing_nullable=False)

    add_column_if_missing("site_announcements", sa.Column("title", sa.String(length=255), nullable=True))
    add_column_if_missing(
        "site_announcements",
        sa.Column("category", sa.String(length=50), nullable=False, server_default="announcement"),
    )
    add_column_if_missing(
        "site_announcements",
        sa.Column("display_placement", sa.String(length=50), nullable=False, server_default="top_banner"),
    )
    add_column_if_missing(
        "site_announcements",
        sa.Column("target_pages", sa.String(length=255), nullable=False, server_default="all"),
    )
    add_column_if_missing("site_announcements", sa.Column("image_url", sa.Text(), nullable=True))
    add_column_if_missing("site_announcements", sa.Column("link_text", sa.String(length=100), nullable=True))
    add_column_if_missing("site_announcements", sa.Column("event_date", sa.DateTime(), nullable=True))
    add_column_if_missing("site_announcements", sa.Column("event_location", sa.String(length=255), nullable=True))
    add_column_if_missing("site_announcements", sa.Column("organizer", sa.String(length=255), nullable=True))
    add_column_if_missing(
        "site_announcements",
        sa.Column("modal_delay_seconds", sa.Integer(), nullable=False, server_default="5"),
    )
    add_column_if_missing("site_announcements", sa.Column("start_date", sa.DateTime(), nullable=True))
    add_column_if_missing("site_announcements", sa.Column("expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for col in (
        "expires_at",
        "start_date",
        "modal_delay_seconds",
        "organizer",
        "event_location",
        "event_date",
        "link_text",
        "image_url",
        "target_pages",
        "display_placement",
        "category",
        "title",
    ):
        drop_column_if_exists("site_announcements", col)
