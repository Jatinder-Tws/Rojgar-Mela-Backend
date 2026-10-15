"""Widen assessment session interest columns so industry + role names fit.

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-10-15 14:35:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import table_exists


revision: str = "s5t6u7v8w9x0"
down_revision: Union[str, None] = "r4s5t6u7v8w9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not table_exists("assessment_sessions"):
        return
    op.alter_column(
        "assessment_sessions",
        "domain_interest",
        existing_type=sa.String(100),
        type_=sa.String(255),
        existing_nullable=True,
    )
    op.alter_column(
        "assessment_sessions",
        "experience_level",
        existing_type=sa.String(50),
        type_=sa.String(100),
        existing_nullable=True,
    )


def downgrade() -> None:
    if not table_exists("assessment_sessions"):
        return
    op.alter_column(
        "assessment_sessions",
        "domain_interest",
        existing_type=sa.String(255),
        type_=sa.String(100),
        existing_nullable=True,
    )
    op.alter_column(
        "assessment_sessions",
        "experience_level",
        existing_type=sa.String(100),
        type_=sa.String(50),
        existing_nullable=True,
    )
