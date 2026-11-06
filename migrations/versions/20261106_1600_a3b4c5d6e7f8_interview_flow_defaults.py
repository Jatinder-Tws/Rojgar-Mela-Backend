"""Interview settings link/location and outcome notes.

Revision ID: a3b4c5d6e7f8
Revises: z2a3b4c5d6e7
Create Date: 2026-11-06 16:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing, drop_column_if_exists

revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "z2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "provider_interview_settings",
        sa.Column("default_interview_type", sa.String(length=20), nullable=False, server_default="video"),
    )
    add_column_if_missing(
        "provider_interview_settings",
        sa.Column("default_meeting_link", sa.Text(), nullable=True),
    )
    add_column_if_missing(
        "provider_interview_settings",
        sa.Column("default_location", sa.Text(), nullable=True),
    )
    add_column_if_missing(
        "interviews",
        sa.Column("outcome_notes", sa.Text(), nullable=True),
    )
    op.execute(
        """
        UPDATE provider_interview_settings
        SET timezone = 'Asia/Kolkata'
        WHERE timezone IS NULL OR btrim(timezone) = '' OR timezone = 'UTC'
        """
    )


def downgrade() -> None:
    drop_column_if_exists("interviews", "outcome_notes")
    drop_column_if_exists("provider_interview_settings", "default_location")
    drop_column_if_exists("provider_interview_settings", "default_meeting_link")
    drop_column_if_exists("provider_interview_settings", "default_interview_type")
