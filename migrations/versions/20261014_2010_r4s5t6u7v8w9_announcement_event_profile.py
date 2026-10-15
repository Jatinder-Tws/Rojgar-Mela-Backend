"""Store modular event content on announcements.

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-10-14 20:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing, drop_column_if_exists, table_exists
from sqlalchemy.dialects import postgresql


revision: str = "r4s5t6u7v8w9"
down_revision: Union[str, None] = "q3r4s5t6u7v8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if table_exists("site_announcements"):
        add_column_if_missing("site_announcements", sa.Column("event_profile", sa.JSON(), nullable=True))
    if table_exists("event_form_submissions"):
        add_column_if_missing(
            "event_form_submissions",
            sa.Column("announcement_id", postgresql.UUID(as_uuid=False), nullable=True),
        )
        op.alter_column("event_form_submissions", "job_fair_id", existing_type=postgresql.UUID(as_uuid=False), nullable=True)


def downgrade() -> None:
    if table_exists("event_form_submissions"):
        drop_column_if_exists("event_form_submissions", "announcement_id")
    if table_exists("site_announcements"):
        drop_column_if_exists("site_announcements", "event_profile")
