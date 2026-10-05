"""Add homepage layout, badge, and tagline to site announcements.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-29 18:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, drop_column_if_exists


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("site_announcements", sa.Column("home_layout", sa.String(length=20), nullable=True))
    add_column_if_missing("site_announcements", sa.Column("badge_label", sa.String(length=80), nullable=True))
    add_column_if_missing("site_announcements", sa.Column("tagline", sa.String(length=255), nullable=True))


def downgrade() -> None:
    drop_column_if_exists("site_announcements", "tagline")
    drop_column_if_exists("site_announcements", "badge_label")
    drop_column_if_exists("site_announcements", "home_layout")
