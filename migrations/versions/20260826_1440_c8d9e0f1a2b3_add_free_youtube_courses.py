"""add training portal free youtube courses

Revision ID: c8d9e0f1a2b3
Revises: b2c3d4e5f6a7
Create Date: 2026-08-26 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.training_portal_free_courses')")).scalar()
    if exists:
        return

    op.create_table(
        "training_portal_free_courses",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_by_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("youtube_url", sa.String(length=500), nullable=False),
        sa.Column("playlist_id", sa.String(length=80), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("channel_title", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("playlist_id"),
    )
    op.create_index("ix_training_portal_free_courses_created_by_id", "training_portal_free_courses", ["created_by_id"])
    op.create_index("ix_training_portal_free_courses_playlist_id", "training_portal_free_courses", ["playlist_id"])
    op.create_index("ix_training_portal_free_courses_status", "training_portal_free_courses", ["status"])

    op.create_table(
        "training_portal_free_course_lessons",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=32), nullable=False),
        sa.Column("youtube_url", sa.String(length=300), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["training_portal_free_courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_training_portal_free_course_lessons_course_id",
        "training_portal_free_course_lessons",
        ["course_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.training_portal_free_courses')")).scalar()
    if not exists:
        return
    op.drop_index("ix_training_portal_free_course_lessons_course_id", table_name="training_portal_free_course_lessons")
    op.drop_table("training_portal_free_course_lessons")
    op.drop_index("ix_training_portal_free_courses_status", table_name="training_portal_free_courses")
    op.drop_index("ix_training_portal_free_courses_playlist_id", table_name="training_portal_free_courses")
    op.drop_index("ix_training_portal_free_courses_created_by_id", table_name="training_portal_free_courses")
    op.drop_table("training_portal_free_courses")
