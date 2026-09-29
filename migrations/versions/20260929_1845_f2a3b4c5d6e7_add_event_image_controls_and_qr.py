"""Add show_content_on_image, gallery_images, and qr_code_url to site announcements.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-29 18:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "site_announcements",
        sa.Column("show_content_on_image", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "site_announcements",
        sa.Column("gallery_images", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "site_announcements",
        sa.Column("qr_code_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("site_announcements", "qr_code_url")
    op.drop_column("site_announcements", "gallery_images")
    op.drop_column("site_announcements", "show_content_on_image")
