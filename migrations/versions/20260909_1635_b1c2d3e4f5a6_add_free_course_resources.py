"""add training portal free course resources

Revision ID: b1c2d3e4f5a6
Revises: 9a8b7c6d5e4f
Create Date: 2026-09-09 16:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "9a8b7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT to_regclass('public.training_portal_free_course_resources')")
    ).scalar()
    if exists:
        return

    op.create_table(
        "training_portal_free_course_resources",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("url", sa.String(length=700), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["training_portal_free_courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_training_portal_free_course_resources_course_id",
        "training_portal_free_course_resources",
        ["course_id"],
    )
    op.create_index(
        "ix_training_portal_free_course_resources_category",
        "training_portal_free_course_resources",
        ["category"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT to_regclass('public.training_portal_free_course_resources')")
    ).scalar()
    if not exists:
        return
    op.drop_index(
        "ix_training_portal_free_course_resources_category",
        table_name="training_portal_free_course_resources",
    )
    op.drop_index(
        "ix_training_portal_free_course_resources_course_id",
        table_name="training_portal_free_course_resources",
    )
    op.drop_table("training_portal_free_course_resources")
