"""Store the generated assessment question set on the session.

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-10-15 16:40:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing, drop_column_if_exists, table_exists


revision: str = "t6u7v8w9x0y1"
down_revision: Union[str, None] = "s5t6u7v8w9x0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if table_exists("assessment_sessions"):
        add_column_if_missing("assessment_sessions", sa.Column("question_plan", sa.JSON(), nullable=True))


def downgrade() -> None:
    if table_exists("assessment_sessions"):
        drop_column_if_exists("assessment_sessions", "question_plan")
