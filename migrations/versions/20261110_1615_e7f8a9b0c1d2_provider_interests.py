"""Persist provider Show Interest on AI matches.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-11-10 16:15:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_interests",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("seeker_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seeker_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "seeker_id", name="uq_provider_interests_provider_seeker"),
    )
    op.create_index("ix_provider_interests_provider_id", "provider_interests", ["provider_id"])
    op.create_index("ix_provider_interests_seeker_id", "provider_interests", ["seeker_id"])
    op.create_index("ix_provider_interests_created_at", "provider_interests", ["created_at"])

    # Recover prior Show Interest actions that only created notifications.
    op.execute(
        sa.text(
            """
            INSERT INTO provider_interests (id, provider_id, seeker_id, created_at)
            SELECT gen_random_uuid(),
                   n.related_user_id,
                   n.user_id,
                   MIN(n.created_at)
            FROM notifications n
            INNER JOIN users provider_u ON provider_u.id = n.related_user_id
            INNER JOIN users seeker_u ON seeker_u.id = n.user_id
            WHERE n.type::text = 'interest'
              AND n.related_user_id IS NOT NULL
              AND n.user_id IS NOT NULL
            GROUP BY n.related_user_id, n.user_id
            ON CONFLICT ON CONSTRAINT uq_provider_interests_provider_seeker DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_provider_interests_created_at", table_name="provider_interests")
    op.drop_index("ix_provider_interests_seeker_id", table_name="provider_interests")
    op.drop_index("ix_provider_interests_provider_id", table_name="provider_interests")
    op.drop_table("provider_interests")
