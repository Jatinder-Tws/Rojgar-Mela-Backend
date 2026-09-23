"""Add the managed universities page catalog.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-23 16:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "university_catalog_categories",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("hint", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_university_catalog_categories_slug", "university_catalog_categories", ["slug"], unique=True)

    op.create_table(
        "university_catalog_courses",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("subtitle", sa.String(length=200), nullable=True),
        sa.Column("badge_text", sa.String(length=80), nullable=True),
        sa.Column("badge_tone", sa.String(length=20), nullable=False, server_default="amber"),
        sa.Column("badge_mode", sa.String(length=30), nullable=False, server_default="custom"),
        sa.Column("icon_key", sa.String(length=40), nullable=False, server_default="graduation"),
        sa.Column("match_course_name", sa.String(length=200), nullable=False),
        sa.Column("match_mode", sa.String(length=20), nullable=False, server_default="exact"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["university_catalog_categories.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_university_catalog_courses_category_id", "university_catalog_courses", ["category_id"])

    op.create_table(
        "university_page_settings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("eyebrow_template", sa.String(length=200), nullable=False),
        sa.Column("lead_template", sa.String(length=200), nullable=False),
        sa.Column("rest_template", sa.String(length=300), nullable=False),
        sa.Column("catalog_seeded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("university_page_settings")
    op.drop_index("ix_university_catalog_courses_category_id", table_name="university_catalog_courses")
    op.drop_table("university_catalog_courses")
    op.drop_index("ix_university_catalog_categories_slug", table_name="university_catalog_categories")
    op.drop_table("university_catalog_categories")
