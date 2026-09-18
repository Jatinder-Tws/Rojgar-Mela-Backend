"""Add site_announcements table for public news ticker.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-18 18:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_announcements",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("text", sa.String(length=280), nullable=False),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_site_announcements_active_sort",
        "site_announcements",
        ["is_active", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_site_announcements_active_sort", table_name="site_announcements")
    op.drop_table("site_announcements")
