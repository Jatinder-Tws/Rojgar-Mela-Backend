"""Cast drifted interview status and type columns back to Postgres enums.

The interviews table was created with interviewstatus / interviewtype, but
status and interview_type were later stored as varchar. SQLAlchemy still
binds those filters as enums, which PostgreSQL rejects:

    operator does not exist: character varying = interviewstatus

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-11-06 16:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# column, enum type, allowed labels, default label
_COLUMNS = (
    ("status", "interviewstatus", ("scheduled", "completed", "cancelled", "no_show"), "scheduled"),
    ("interview_type", "interviewtype", ("video", "walk_in"), "video"),
)


def _udt(column: str) -> str | None:
    row = op.get_bind().execute(
        sa.text(
            """
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'interviews'
              AND column_name = :column
            """
        ),
        {"column": column},
    ).first()
    return row[0] if row else None


def _ensure_enum(name: str, labels: tuple[str, ...]) -> None:
    exists = op.get_bind().execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": name},
    ).first()
    if exists:
        return
    quoted = ", ".join("'" + label.replace("'", "''") + "'" for label in labels)
    op.execute(f"CREATE TYPE {name} AS ENUM ({quoted})")


def upgrade() -> None:
    bind = op.get_bind()
    for column, enum_name, labels, default in _COLUMNS:
        udt = _udt(column)
        if udt is None or udt == enum_name:
            continue
        if udt not in {"varchar", "text"}:
            raise RuntimeError(
                f"interviews.{column} is {udt}; expected varchar or {enum_name}"
            )
        _ensure_enum(enum_name, labels)
        bad = bind.execute(
            sa.text(
                f"""
                SELECT DISTINCT {column}
                FROM interviews
                WHERE {column} IS NOT NULL
                  AND {column} NOT IN :allowed
                """
            ).bindparams(sa.bindparam("allowed", expanding=True)),
            {"allowed": list(labels)},
        ).fetchall()
        if bad:
            values = ", ".join(str(row[0]) for row in bad)
            raise RuntimeError(
                f"interviews.{column} has values outside {enum_name}: {values}"
            )
        op.execute(f"ALTER TABLE interviews ALTER COLUMN {column} DROP DEFAULT")
        op.execute(
            f"""
            ALTER TABLE interviews
            ALTER COLUMN {column} TYPE {enum_name}
            USING {column}::{enum_name}
            """
        )
        op.execute(
            f"ALTER TABLE interviews ALTER COLUMN {column} SET DEFAULT '{default}'::{enum_name}"
        )


def downgrade() -> None:
    for column, enum_name, _labels, default in _COLUMNS:
        if _udt(column) != enum_name:
            continue
        op.execute(f"ALTER TABLE interviews ALTER COLUMN {column} DROP DEFAULT")
        op.execute(
            f"""
            ALTER TABLE interviews
            ALTER COLUMN {column} TYPE VARCHAR(20)
            USING {column}::text
            """
        )
        op.execute(
            f"ALTER TABLE interviews ALTER COLUMN {column} SET DEFAULT '{default}'"
        )
