"""add resources column to career_roadmaps

Revision ID: a1b2c3d4e5f6
Revises: c7a91d4e2b18
Create Date: 2026-08-25 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c7a91d4e2b18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.career_roadmaps')")).scalar()
    if not exists:
        return
    cols = {
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'career_roadmaps'"
            )
        )
    }
    if "resources" in cols:
        return
    op.add_column(
        "career_roadmaps",
        sa.Column(
            "resources",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.career_roadmaps')")).scalar()
    if not exists:
        return
    cols = {
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'career_roadmaps'"
            )
        )
    }
    if "resources" not in cols:
        return
    op.drop_column("career_roadmaps", "resources")
