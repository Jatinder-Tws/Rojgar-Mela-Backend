"""Add homepage layout, badge, and tagline to site announcements.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-29 18:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("site_announcements", sa.Column("home_layout", sa.String(length=20), nullable=True))
    op.add_column("site_announcements", sa.Column("badge_label", sa.String(length=80), nullable=True))
    op.add_column("site_announcements", sa.Column("tagline", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("site_announcements", "tagline")
    op.drop_column("site_announcements", "badge_label")
    op.drop_column("site_announcements", "home_layout")
