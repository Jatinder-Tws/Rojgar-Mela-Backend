"""add supervisor_profiles table and supervisor userrole

Revision ID: f5a6b7c8d9e0
Revises: 6b448b1badcd
Create Date: 2026-08-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, None] = "6b448b1badcd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add supervisor value to userrole enum if it does not already exist
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumlabel = 'supervisor'
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')
                ) THEN
                    ALTER TYPE userrole ADD VALUE 'supervisor';
                END IF;
            END$$;
            """
        )
    )

    # 2. Create supervisor_profiles table
    op.create_table(
        "supervisor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("permissions", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index(
        "ix_supervisor_profiles_user_id",
        "supervisor_profiles",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "ix_supervisor_profiles_is_active",
        "supervisor_profiles",
        ["is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_supervisor_profiles_is_active", table_name="supervisor_profiles")
    op.drop_index("ix_supervisor_profiles_user_id", table_name="supervisor_profiles")
    op.drop_table("supervisor_profiles")
