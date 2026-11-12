"""Add source_portal to audit_logs and backfill from request_path.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-11-12 14:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from migrations.helpers import (
    add_column_if_missing,
    create_index_if_missing,
    drop_column_if_exists,
    drop_index_if_exists,
    execute_if_columns,
)

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "audit_logs",
        sa.Column("source_portal", sa.String(40), nullable=True),
    )
    create_index_if_missing("ix_audit_logs_source_portal", "audit_logs", ["source_portal"])
    create_index_if_missing(
        "ix_audit_logs_portal_created",
        "audit_logs",
        ["source_portal", "created_at"],
    )

    # Backfill from path prefixes where possible.
    execute_if_columns(
        "audit_logs",
        ["source_portal", "request_path"],
        """
        UPDATE audit_logs
        SET source_portal = 'training_portal'
        WHERE source_portal IS NULL
          AND (
            request_path ILIKE '/training-portal%'
            OR request_path ILIKE '/google-calendar%'
          )
        """,
    )
    execute_if_columns(
        "audit_logs",
        ["source_portal", "request_path"],
        """
        UPDATE audit_logs
        SET source_portal = 'auth'
        WHERE source_portal IS NULL
          AND (
            request_path ILIKE '/auth%'
            OR request_path ILIKE '/supervisor/login%'
            OR (request_path ILIKE '/superadmin%' AND request_path ILIKE '%login%')
          )
        """,
    )
    execute_if_columns(
        "audit_logs",
        ["source_portal"],
        """
        UPDATE audit_logs
        SET source_portal = 'job_portal'
        WHERE source_portal IS NULL
        """,
    )


def downgrade() -> None:
    drop_index_if_exists("ix_audit_logs_portal_created", "audit_logs")
    drop_index_if_exists("ix_audit_logs_source_portal", "audit_logs")
    drop_column_if_exists("audit_logs", "source_portal")
