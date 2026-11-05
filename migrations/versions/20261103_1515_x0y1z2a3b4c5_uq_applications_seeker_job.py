"""Partial unique index: one application per seeker per job

Revision ID: x0y1z2a3b4c5
Revises: w9x0y1z2a3b4
Create Date: 2026-11-03 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "x0y1z2a3b4c5"
down_revision: Union[str, None] = "w9x0y1z2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "uq_applications_seeker_job"


def upgrade() -> None:
    # Keep the earliest application when duplicates already exist.
    op.execute(
        """
        DELETE FROM applications
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY seeker_id, job_id
                           ORDER BY applied_at ASC NULLS LAST, id ASC
                       ) AS rn
                FROM applications
                WHERE seeker_id IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
        """
    )
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
        ON applications (seeker_id, job_id)
        WHERE seeker_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
