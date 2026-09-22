"""Add lead follow-up CRM fields and remap enquiry statuses.

Revision ID: a7b8c9d0e1f2
Revises: 3531b13e7900
Create Date: 2026-09-22 14:35:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "3531b13e7900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FOLLOW_UP_COLUMNS = (
    ("last_contact_date", sa.DateTime()),
    ("next_follow_up_date", sa.DateTime()),
    ("preferred_call_time", sa.String(length=120)),
    ("interested_after_fee", sa.String(length=20)),
    ("main_objection", sa.String(length=255)),
    ("final_outcome", sa.Text()),
)

TABLES = ("career_enquiries", "contact_inquiries")


def upgrade() -> None:
    for table in TABLES:
        for column_name, column_type in FOLLOW_UP_COLUMNS:
            op.add_column(table, sa.Column(column_name, column_type, nullable=True))

        op.execute(
            f"UPDATE {table} SET status = 'follow_up_required' WHERE status = 'in_progress'"
        )
        op.execute(f"UPDATE {table} SET status = 'converted' WHERE status = 'enrolled'")
        op.execute(
            f"UPDATE {table} SET status = 'lost' WHERE status IN ('not_interested', 'closed')"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(
            f"UPDATE {table} SET status = 'in_progress' WHERE status = 'follow_up_required'"
        )
        op.execute(f"UPDATE {table} SET status = 'enrolled' WHERE status = 'converted'")
        op.execute(
            f"UPDATE {table} SET status = 'not_interested' "
            f"WHERE status IN ('lost', 'visit_scheduled', 'counselling_done')"
        )
        for column_name, _ in reversed(FOLLOW_UP_COLUMNS):
            op.drop_column(table, column_name)
