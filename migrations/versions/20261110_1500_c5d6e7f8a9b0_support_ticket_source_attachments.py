"""Add support ticket source + message attachments (same tables).

Keeps one support_tickets / ticket_messages pair for job portal and training,
with source to separate queues and optional screenshot attachments on messages.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-11-10 15:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_CATEGORIES = ("attendance", "class_schedule")


def _enum_labels(type_name: str) -> set[str]:
    rows = op.get_bind().execute(
        sa.text(
            """
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON e.enumtypid = t.oid
            WHERE t.typname = :name
            """
        ),
        {"name": type_name},
    ).fetchall()
    return {r[0] for r in rows}


def upgrade() -> None:
    bind = op.get_bind()
    existing = _enum_labels("ticketcategory")
    for label in _NEW_CATEGORIES:
        if label in existing:
            continue
        # ALTER TYPE … ADD VALUE cannot run inside a transaction block on older PG;
        # autocommit_block is the safe Alembic pattern.
        with op.get_context().autocommit_block():
            op.execute(sa.text(f"ALTER TYPE ticketcategory ADD VALUE '{label}'"))

    op.add_column(
        "support_tickets",
        sa.Column("source", sa.String(length=32), nullable=False, server_default="job_portal"),
    )
    op.create_index(op.f("ix_support_tickets_source"), "support_tickets", ["source"], unique=False)

    # Legacy training tickets used subject prefixes instead of real categories.
    bind.execute(
        sa.text(
            """
            UPDATE support_tickets
            SET source = 'training',
                category = 'attendance',
                subject = regexp_replace(subject, '^\\[Attendance Issue\\]\\s*', '')
            WHERE subject LIKE '[Attendance Issue]%'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE support_tickets
            SET source = 'training',
                category = 'class_schedule',
                subject = regexp_replace(subject, '^\\[Class Schedule\\]\\s*', '')
            WHERE subject LIKE '[Class Schedule]%'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE support_tickets st
            SET source = 'training'
            FROM users u
            WHERE st.user_id = u.id
              AND u.role = 'teacher'
              AND st.source = 'job_portal'
            """
        )
    )

    op.add_column("ticket_messages", sa.Column("attachment_url", sa.String(length=500), nullable=True))
    op.add_column("ticket_messages", sa.Column("attachment_filename", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("ticket_messages", "attachment_filename")
    op.drop_column("ticket_messages", "attachment_url")
    op.drop_index(op.f("ix_support_tickets_source"), table_name="support_tickets")
    op.drop_column("support_tickets", "source")
    # Postgres cannot easily remove enum values; leave attendance/class_schedule in place.
