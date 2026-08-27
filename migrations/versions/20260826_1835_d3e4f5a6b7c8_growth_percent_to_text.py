"""store career roadmap growth as text

Revision ID: d3e4f5a6b7c8
Revises: 6b448b1badcd
Create Date: 2026-08-26 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "6b448b1badcd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ALTER COLUMN growth_percent TYPE VARCHAR(80)
            USING CASE
                WHEN growth_percent IS NULL THEN NULL
                ELSE NULLIF(
                    trim(trailing '.' FROM trim(trailing '0' FROM growth_percent::text)),
                    ''
                )
            END
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ALTER COLUMN growth_percent TYPE DOUBLE PRECISION
            USING NULLIF(regexp_replace(growth_percent, '[^0-9.+-]', '', 'g'), '')::double precision
            """
        )
    )
