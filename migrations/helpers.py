"""Safe, idempotent helpers for Alembic upgrades.

Use these when a migration may run against a DB that already has the
schema change (manual fix, partial apply, or create_all drift).
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

import sqlalchemy as sa
from alembic import op


def _inspector():
    return sa.inspect(op.get_bind())


def table_exists(table: str) -> bool:
    return _inspector().has_table(table)


def column_names(table: str) -> set[str]:
    insp = _inspector()
    if not insp.has_table(table):
        return set()
    return {col["name"] for col in insp.get_columns(table)}


def index_names(table: str) -> set[str]:
    insp = _inspector()
    if not insp.has_table(table):
        return set()
    return {idx["name"] for idx in insp.get_indexes(table) if idx.get("name")}


def unique_constraint_names(table: str) -> set[str]:
    insp = _inspector()
    if not insp.has_table(table):
        return set()
    return {uc["name"] for uc in insp.get_unique_constraints(table) if uc.get("name")}


def add_column_if_missing(table: str, column: sa.Column) -> bool:
    if column.name in column_names(table):
        return False
    op.add_column(table, column)
    return True


def create_index_if_missing(
    name: str,
    table: str,
    columns: Sequence[str],
    *,
    unique: bool = False,
) -> bool:
    if not table_exists(table) or name in index_names(table):
        return False
    op.create_index(name, table, list(columns), unique=unique)
    return True


def drop_column_if_exists(table: str, column: str) -> bool:
    if column not in column_names(table):
        return False
    op.drop_column(table, column)
    return True


def drop_index_if_exists(name: str, table: str) -> bool:
    if not table_exists(table) or name not in index_names(table):
        return False
    op.drop_index(name, table_name=table)
    return True


def drop_table_if_exists(table: str) -> bool:
    if not table_exists(table):
        return False
    op.drop_table(table)
    return True


def execute_if_columns(table: str, required: Iterable[str], sql: str) -> bool:
    """Run raw SQL only when every required column exists on the table."""
    cols = column_names(table)
    needed = set(required)
    if not needed.issubset(cols):
        return False
    op.execute(sql)
    return True


def first_existing_column(table: str, candidates: Sequence[str]) -> Optional[str]:
    cols = column_names(table)
    for name in candidates:
        if name in cols:
            return name
    return None
