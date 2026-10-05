"""Add show_content_on_image, gallery_images, and qr_code_url to site announcements.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-29 18:45:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, drop_column_if_exists


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "site_announcements",
        sa.Column("show_content_on_image", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    add_column_if_missing(
        "site_announcements",
        sa.Column("gallery_images", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
    )
    add_column_if_missing(
        "site_announcements",
        sa.Column("qr_code_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    drop_column_if_exists("site_announcements", "qr_code_url")
    drop_column_if_exists("site_announcements", "gallery_images")
    drop_column_if_exists("site_announcements", "show_content_on_image")
