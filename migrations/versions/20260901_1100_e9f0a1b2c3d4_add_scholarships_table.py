"""add scholarships table for unstop and buddy4study opportunities

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-09-01 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create scholarships table
    op.create_table(
        "scholarships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(150), nullable=False),
        sa.Column("source_platform", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), nullable=True),
        sa.Column("organization_name", sa.String(300), nullable=True),
        sa.Column("organization_logo", sa.String(1000), nullable=True),
        sa.Column("banner_image", sa.String(1000), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("eligibility_criteria", sa.Text(), nullable=True),
        sa.Column("award_amount", sa.String(200), nullable=True),
        sa.Column("award_type", sa.String(100), nullable=True),
        sa.Column("currency", sa.String(10), server_default="INR", nullable=False),
        sa.Column("target_education_levels", sa.JSON(), nullable=True),
        sa.Column("gender_eligibility", sa.String(50), server_default="All", nullable=True),
        sa.Column("region_or_country", sa.String(100), server_default="India", nullable=True),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("application_url", sa.String(1000), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_platform", "external_id", name="uq_scholarship_source_external_id"),
    )

    # 2. Create indexes
    op.create_index("ix_scholarships_external_id", "scholarships", ["external_id"])
    op.create_index("ix_scholarships_source_platform", "scholarships", ["source_platform"])
    op.create_index("ix_scholarships_title", "scholarships", ["title"])
    op.create_index("ix_scholarships_slug", "scholarships", ["slug"])
    op.create_index("ix_scholarships_organization_name", "scholarships", ["organization_name"])
    op.create_index("ix_scholarships_deadline", "scholarships", ["deadline"])
    op.create_index("ix_scholarships_is_featured", "scholarships", ["is_featured"])
    op.create_index("ix_scholarships_is_active", "scholarships", ["is_active"])
    op.create_index("ix_scholarships_platform_active", "scholarships", ["source_platform", "is_active"])
    op.create_index("ix_scholarships_deadline_active", "scholarships", ["deadline", "is_active"])


def downgrade() -> None:
    op.drop_table("scholarships")
