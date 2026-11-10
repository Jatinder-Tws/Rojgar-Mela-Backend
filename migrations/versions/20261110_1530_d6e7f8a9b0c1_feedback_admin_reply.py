"""Add admin reply fields on platform_feedback (same table).

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-11-10 15:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("platform_feedback", sa.Column("admin_reply", sa.Text(), nullable=True))
    op.add_column(
        "platform_feedback",
        sa.Column("admin_replied_by", sa.UUID(as_uuid=False), nullable=True),
    )
    op.add_column("platform_feedback", sa.Column("admin_replied_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(
        "fk_platform_feedback_admin_replied_by_users",
        "platform_feedback",
        "users",
        ["admin_replied_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_platform_feedback_admin_replied_by_users", "platform_feedback", type_="foreignkey")
    op.drop_column("platform_feedback", "admin_replied_at")
    op.drop_column("platform_feedback", "admin_replied_by")
    op.drop_column("platform_feedback", "admin_reply")
