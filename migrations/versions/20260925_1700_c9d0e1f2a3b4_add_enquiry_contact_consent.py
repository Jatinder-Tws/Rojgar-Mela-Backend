"""Store contact consent for manually created enquiries.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-25 17:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from migrations.helpers import add_column_if_missing, drop_column_if_exists


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "career_enquiries",
        sa.Column("consent_to_contact", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    drop_column_if_exists("career_enquiries", "consent_to_contact")
