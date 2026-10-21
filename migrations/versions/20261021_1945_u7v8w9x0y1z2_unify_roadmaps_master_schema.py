"""Unify roadmaps table to be the master table for public, seeker, and admin.

Revision ID: u7v8w9x0y1z2
Revises: t6u7v8w9x0y1
Create Date: 2026-10-21 19:45:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import (
    add_column_if_missing,
    create_index_if_missing,
    drop_column_if_exists,
    table_exists,
)


revision: str = "u7v8w9x0y1z2"
down_revision: Union[str, None] = "t6u7v8w9x0y1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if table_exists("roadmaps"):
        # Make user_id nullable so roadmaps can have master/global templates
        op.alter_column("roadmaps", "user_id", nullable=True)

        # Add metadata and presentation columns for unified catalog
        add_column_if_missing("roadmaps", sa.Column("slug", sa.String(200), nullable=True))
        add_column_if_missing(
            "roadmaps",
            sa.Column("category", sa.String(100), server_default="Technology", nullable=False),
        )
        add_column_if_missing("roadmaps", sa.Column("short_description", sa.Text(), nullable=True))
        add_column_if_missing("roadmaps", sa.Column("long_description", sa.Text(), nullable=True))
        add_column_if_missing(
            "roadmaps",
            sa.Column("industries", sa.JSON(), server_default="[]", nullable=True),
        )
        add_column_if_missing("roadmaps", sa.Column("salary_lpa", sa.String(80), nullable=True))
        add_column_if_missing("roadmaps", sa.Column("growth_percent", sa.String(80), nullable=True))
        add_column_if_missing("roadmaps", sa.Column("openings_count", sa.String(80), nullable=True))
        add_column_if_missing("roadmaps", sa.Column("hero_image_url", sa.String(500), nullable=True))
        add_column_if_missing(
            "roadmaps",
            sa.Column("is_published", sa.Boolean(), server_default="true", nullable=False),
        )
        add_column_if_missing(
            "roadmaps",
            sa.Column("is_featured", sa.Boolean(), server_default="false", nullable=False),
        )
        add_column_if_missing(
            "roadmaps",
            sa.Column("is_trending", sa.Boolean(), server_default="false", nullable=False),
        )
        add_column_if_missing(
            "roadmaps",
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        )
        add_column_if_missing(
            "roadmaps",
            sa.Column("career_insights", sa.JSON(), server_default="{}", nullable=True),
        )
        add_column_if_missing(
            "roadmaps",
            sa.Column("faqs", sa.JSON(), server_default="[]", nullable=True),
        )

        create_index_if_missing("ix_roadmaps_slug", "roadmaps", ["slug"])
        create_index_if_missing("ix_roadmaps_is_published", "roadmaps", ["is_published"])


def downgrade() -> None:
    if table_exists("roadmaps"):
        drop_column_if_exists("roadmaps", "faqs")
        drop_column_if_exists("roadmaps", "career_insights")
        drop_column_if_exists("roadmaps", "sort_order")
        drop_column_if_exists("roadmaps", "is_trending")
        drop_column_if_exists("roadmaps", "is_featured")
        drop_column_if_exists("roadmaps", "is_published")
        drop_column_if_exists("roadmaps", "hero_image_url")
        drop_column_if_exists("roadmaps", "openings_count")
        drop_column_if_exists("roadmaps", "growth_percent")
        drop_column_if_exists("roadmaps", "salary_lpa")
        drop_column_if_exists("roadmaps", "industries")
        drop_column_if_exists("roadmaps", "long_description")
        drop_column_if_exists("roadmaps", "short_description")
        drop_column_if_exists("roadmaps", "category")
        drop_column_if_exists("roadmaps", "slug")
