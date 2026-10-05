"""Add occurrence_reports JSON to training portal class sessions.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-15 16:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, drop_column_if_exists


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    added = add_column_if_missing(
        "training_portal_class_sessions",
        sa.Column("occurrence_reports", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    if added:
        op.alter_column("training_portal_class_sessions", "occurrence_reports", server_default=None)


def downgrade() -> None:
    drop_column_if_exists("training_portal_class_sessions", "occurrence_reports")
