"""add career_roadmaps table

Revision ID: c7a91d4e2b18
Revises: 64ea0e54e9d6
Create Date: 2026-08-24 14:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c7a91d4e2b18"
down_revision: Union[str, None] = "64ea0e54e9d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.career_roadmaps')")).scalar()
    if exists:
        return

    op.create_table(
        "career_roadmaps",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), server_default="Technology", nullable=False),
        sa.Column("level", sa.String(length=50), server_default="Intermediate", nullable=False),
        sa.Column(
            "industries",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("long_description", sa.Text(), nullable=True),
        sa.Column(
            "skill_tags",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("duration_months", sa.Integer(), nullable=True),
        sa.Column("salary_lpa", sa.Float(), nullable=True),
        sa.Column("growth_percent", sa.Float(), nullable=True),
        sa.Column("openings_count", sa.Integer(), nullable=True),
        sa.Column(
            "steps",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("hero_image_url", sa.String(length=500), nullable=True),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_featured",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_trending",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_by", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_career_roadmaps_slug"), "career_roadmaps", ["slug"], unique=True)
    op.create_index(op.f("ix_career_roadmaps_is_published"), "career_roadmaps", ["is_published"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.career_roadmaps')")).scalar()
    if not exists:
        return

    op.drop_index(op.f("ix_career_roadmaps_is_published"), table_name="career_roadmaps")
    op.drop_index(op.f("ix_career_roadmaps_slug"), table_name="career_roadmaps")
    op.drop_table("career_roadmaps")
