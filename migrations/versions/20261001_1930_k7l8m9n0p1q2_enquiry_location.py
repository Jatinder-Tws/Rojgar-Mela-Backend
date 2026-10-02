"""Store enquiry location for the lead list.

Revision ID: k7l8m9n0p1q2
Revises: j6k7l8m9n0p1
Create Date: 2026-10-01 19:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k7l8m9n0p1q2"
down_revision: Union[str, None] = "j6k7l8m9n0p1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {col["name"] for col in inspector.get_columns("career_enquiries")}
    if "location" not in cols:
        op.add_column("career_enquiries", sa.Column("location", sa.String(200), nullable=True))
    if "event_lucky_entries" in inspector.get_table_names():
        op.execute(
            """
            UPDATE career_enquiries AS ce
            SET location = NULLIF(BTRIM(ele.location), '')
            FROM event_lucky_entries AS ele
            WHERE ele.enquiry_id IS NOT NULL
              AND ele.enquiry_id::text = ce.id::text
              AND (ce.location IS NULL OR BTRIM(ce.location) = '')
            """
        )
    op.execute(
        """
        UPDATE career_enquiries
        SET location = NULLIF(BTRIM(substring(message from 'Location: ([^\\n]+)')), '-')
        WHERE (location IS NULL OR BTRIM(location) = '')
          AND message IS NOT NULL
          AND message ~ 'Location:'
        """
    )


def downgrade() -> None:
    op.drop_column("career_enquiries", "location")
