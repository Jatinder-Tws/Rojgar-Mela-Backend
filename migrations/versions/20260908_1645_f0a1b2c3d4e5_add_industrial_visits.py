"""add industrial visits tables and merge alembic heads

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4, e4f5a6b7c8d9
Create Date: 2026-09-08 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "fd2866df6b5f" 
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "industrial_visits",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("visit_date", sa.DateTime(), nullable=False),
        sa.Column("venue", sa.String(300), nullable=True),
        sa.Column("college_name", sa.String(200), nullable=True),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("check_in_slug", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("certificates_sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_industrial_visits_slug"),
        sa.UniqueConstraint("check_in_slug", name="uq_industrial_visits_check_in_slug"),
    )
    op.create_index("ix_industrial_visits_slug", "industrial_visits", ["slug"])
    op.create_index("ix_industrial_visits_check_in_slug", "industrial_visits", ["check_in_slug"])
    op.create_index("ix_industrial_visits_is_active", "industrial_visits", ["is_active"])

    op.create_table(
        "industrial_visit_students",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("visit_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("college_name", sa.String(200), nullable=False),
        sa.Column("department", sa.String(80), nullable=False),
        sa.Column("year_of_study", sa.String(40), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("location", sa.String(120), nullable=False),
        sa.Column("area_of_interest", sa.String(200), nullable=False),
        sa.Column("graduation_year", sa.String(10), nullable=False),
        sa.Column("attendance_status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("attended_at", sa.DateTime(), nullable=True),
        sa.Column("certificate_status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("certificate_sent_at", sa.DateTime(), nullable=True),
        sa.Column("certificate_id", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["industrial_visits.id"],
            name="fk_industrial_visit_students_visit_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("visit_id", "email", name="uq_industrial_visit_student_email"),
        sa.UniqueConstraint("certificate_id", name="uq_industrial_visit_student_certificate_id"),
    )
    op.create_index("ix_industrial_visit_students_visit_id", "industrial_visit_students", ["visit_id"])
    op.create_index("ix_industrial_visit_students_email", "industrial_visit_students", ["email"])
    op.create_index("ix_iv_students_phone", "industrial_visit_students", ["phone"])
    op.create_index("ix_iv_students_visit_attendance", "industrial_visit_students", ["visit_id", "attendance_status"])
    op.create_index("ix_iv_students_visit_certificate", "industrial_visit_students", ["visit_id", "certificate_status"])
    op.create_index("ix_industrial_visit_students_certificate_id", "industrial_visit_students", ["certificate_id"])


def downgrade() -> None:
    op.drop_table("industrial_visit_students")
    op.drop_table("industrial_visits")
