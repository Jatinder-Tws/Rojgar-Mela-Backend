"""Store modular event creator content on job fairs.

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-10-14 19:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing, drop_column_if_exists, drop_table_if_exists, table_exists
from sqlalchemy.dialects import postgresql


revision: str = "q3r4s5t6u7v8"
down_revision: Union[str, None] = "p2q3r4s5t6u7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if table_exists("job_fairs"):
        add_column_if_missing("job_fairs", sa.Column("event_profile", sa.JSON(), nullable=True))
    if not table_exists("event_form_submissions"):
        op.create_table(
            "event_form_submissions",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("job_fair_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("job_fairs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_event_form_submissions_job_fair_id", "event_form_submissions", ["job_fair_id"])


def downgrade() -> None:
    drop_table_if_exists("event_form_submissions")
    if table_exists("job_fairs"):
        drop_column_if_exists("job_fairs", "event_profile")
