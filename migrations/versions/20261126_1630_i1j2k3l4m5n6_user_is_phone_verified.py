"""Add is_phone_verified column to users table.

Revision ID: i1j2k3l4m5n6
Revises: h0i1j2k3l4m5
Create Date: 2026-11-26 16:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing, drop_column_if_exists

revision: str = "i1j2k3l4m5n6"
down_revision: Union[str, None] = "h0i1j2k3l4m5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "users",
        sa.Column(
            "is_phone_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    drop_column_if_exists("users", "is_phone_verified")
