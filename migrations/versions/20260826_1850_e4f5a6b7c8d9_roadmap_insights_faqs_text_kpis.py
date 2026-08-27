"""roadmap overview text KPIs, insights, faqs, richer steps

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-26 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ALTER COLUMN duration_months TYPE VARCHAR(80)
            USING CASE
                WHEN duration_months IS NULL THEN NULL
                ELSE duration_months::text || ' months'
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ALTER COLUMN salary_lpa TYPE VARCHAR(80)
            USING CASE
                WHEN salary_lpa IS NULL THEN NULL
                ELSE '₹' || trim(trailing '.' FROM trim(trailing '0' FROM salary_lpa::text)) || 'L'
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ALTER COLUMN openings_count TYPE VARCHAR(80)
            USING CASE
                WHEN openings_count IS NULL THEN NULL
                ELSE openings_count::text || '+'
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ADD COLUMN IF NOT EXISTS career_insights JSON
            DEFAULT '{}'::json
            NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ADD COLUMN IF NOT EXISTS faqs JSON
            DEFAULT '[]'::json
            NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("career_roadmaps", "faqs")
    op.drop_column("career_roadmaps", "career_insights")
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ALTER COLUMN openings_count TYPE INTEGER
            USING NULLIF(regexp_replace(openings_count, '[^0-9]', '', 'g'), '')::integer
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ALTER COLUMN salary_lpa TYPE DOUBLE PRECISION
            USING NULLIF(regexp_replace(salary_lpa, '[^0-9.+-]', '', 'g'), '')::double precision
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE career_roadmaps
            ALTER COLUMN duration_months TYPE INTEGER
            USING NULLIF(regexp_replace(duration_months, '[^0-9]', '', 'g'), '')::integer
            """
        )
    )
