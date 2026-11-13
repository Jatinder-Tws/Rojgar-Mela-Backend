"""Record who created a user account.

Revision ID: g9h0i1j2k3l4
Revises: f8a9b0c1d2e3
Create Date: 2026-11-13 16:15:00.000000
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

revision: str = "g9h0i1j2k3l4"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_NAME = "fk_users_created_by_id"


def _fk_names(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return set()
    return {fk.get("name") for fk in insp.get_foreign_keys(table) if fk.get("name")}


def upgrade() -> None:
    add_column_if_missing(
        "users",
        sa.Column("created_by_id", sa.UUID(as_uuid=False), nullable=True),
    )
    add_column_if_missing(
        "users",
        sa.Column("account_origin", sa.String(length=32), nullable=True),
    )
    if FK_NAME not in _fk_names("users"):
        op.create_foreign_key(FK_NAME, "users", "users", ["created_by_id"], ["id"], ondelete="SET NULL")
    create_index_if_missing("ix_users_created_by_id", "users", ["created_by_id"])
    create_index_if_missing("ix_users_account_origin", "users", ["account_origin"])

    # Staff-created seekers already have a CREATE audit row. Self signups do not.
    execute_if_columns(
        "audit_logs",
        ["entity_id", "actor_id", "actor_role", "action", "entity_type", "created_at"],
        """
        UPDATE users AS u
        SET created_by_id = src.actor_id,
            account_origin = src.origin
        FROM (
            SELECT DISTINCT ON (entity_id)
                entity_id,
                actor_id,
                CASE
                    WHEN lower(actor_role) IN ('superadmin', 'super_admin') THEN 'superadmin'
                    WHEN lower(actor_role) = 'supervisor' THEN 'supervisor'
                    ELSE lower(actor_role)
                END AS origin
            FROM audit_logs
            WHERE action = 'CREATE'
              AND entity_type = 'seeker'
              AND actor_id IS NOT NULL
              AND entity_id IS NOT NULL
            ORDER BY entity_id, created_at ASC
        ) AS src
        WHERE u.account_origin IS NULL
          AND u.role::text = 'seeker'
          AND u.id::text = src.entity_id
          AND src.actor_id::text <> u.id::text
          AND EXISTS (SELECT 1 FROM users AS creator WHERE creator.id = src.actor_id)
        """,
    )


def downgrade() -> None:
    if FK_NAME in _fk_names("users"):
        op.drop_constraint(FK_NAME, "users", type_="foreignkey")
    drop_index_if_exists("ix_users_account_origin", "users")
    drop_index_if_exists("ix_users_created_by_id", "users")
    drop_column_if_exists("users", "account_origin")
    drop_column_if_exists("users", "created_by_id")
