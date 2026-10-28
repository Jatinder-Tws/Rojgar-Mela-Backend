"""add category column to free courses

Revision ID: w9x0y1z2a3b4
Revises: v8w9x0y1z2a3
Create Date: 2026-10-28 16:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, create_index_if_missing, drop_column_if_exists, drop_index_if_exists

revision: str = "w9x0y1z2a3b4"
down_revision: Union[str, None] = "v8w9x0y1z2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "training_portal_free_courses",
        sa.Column("category", sa.String(length=100), nullable=True),
    )
    create_index_if_missing(
        "ix_training_portal_free_courses_category",
        "training_portal_free_courses",
        ["category"],
    )


def downgrade() -> None:
    drop_index_if_exists("ix_training_portal_free_courses_category", "training_portal_free_courses")
    drop_column_if_exists("training_portal_free_courses", "category")
