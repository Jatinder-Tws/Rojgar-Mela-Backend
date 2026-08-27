"""add career_roadmap_options table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-26 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.career_roadmap_options')")).scalar()
    if exists:
        return

    op.create_table(
        "career_roadmap_options",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "name", name="uq_career_roadmap_options_kind_name"),
    )
    op.create_index("ix_career_roadmap_options_kind", "career_roadmap_options", ["kind"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.career_roadmap_options')")).scalar()
    if not exists:
        return
    op.drop_index("ix_career_roadmap_options_kind", table_name="career_roadmap_options")
    op.drop_table("career_roadmap_options")
