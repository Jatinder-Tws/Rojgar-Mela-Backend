"""Add interest and query fields for lucky-event registrations and enquiries.

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-10-08 18:55:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing, drop_column_if_exists, table_exists


revision: str = "p2q3r4s5t6u7"
down_revision: Union[str, None] = "o1p2q3r4s5t6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if table_exists("event_lucky_entries"):
        add_column_if_missing("event_lucky_entries", sa.Column("interests", sa.Text(), nullable=True))
        add_column_if_missing("event_lucky_entries", sa.Column("visitor_query", sa.Text(), nullable=True))
    if table_exists("career_enquiries"):
        add_column_if_missing("career_enquiries", sa.Column("interests", sa.Text(), nullable=True))
        add_column_if_missing("career_enquiries", sa.Column("visitor_query", sa.Text(), nullable=True))


def downgrade() -> None:
    if table_exists("career_enquiries"):
        drop_column_if_exists("career_enquiries", "visitor_query")
        drop_column_if_exists("career_enquiries", "interests")
    if table_exists("event_lucky_entries"):
        drop_column_if_exists("event_lucky_entries", "visitor_query")
        drop_column_if_exists("event_lucky_entries", "interests")
