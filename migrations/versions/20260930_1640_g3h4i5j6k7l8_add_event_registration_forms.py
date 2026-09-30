"""Add event registration forms, prizes, submissions, and enquiry event fields.

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-30 16:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "g3h4i5j6k7l8"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_registration_forms",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("event_name", sa.String(200), nullable=False),
        sa.Column("booth_location", sa.String(200), nullable=True),
        sa.Column("headline", sa.String(200), nullable=False, server_default="Get Your Lucky Scratch Ticket"),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("badge_label", sa.String(80), nullable=True),
        sa.Column("cta_label", sa.String(120), nullable=False, server_default="Register & Get Random Lucky Ticket"),
        sa.Column("ticket_prefix", sa.String(12), nullable=False, server_default="TKT"),
        sa.Column("lucky_draw_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fields", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("thank_you_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_event_registration_forms_slug", "event_registration_forms", ["slug"], unique=True)

    op.create_table(
        "event_registration_prizes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("form_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("worth_value", sa.String(80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_inventory", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_inventory", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_weight", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("voucher_expiry_days", sa.Integer(), nullable=True),
        sa.Column("redemption_instructions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["form_id"], ["event_registration_forms.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_event_registration_prizes_form_id", "event_registration_prizes", ["form_id"])

    op.create_table(
        "event_registration_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("form_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("enquiry_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("visitor_role", sa.String(120), nullable=True),
        sa.Column("organization", sa.String(200), nullable=True),
        sa.Column("interest", sa.String(200), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ticket_number", sa.String(40), nullable=True),
        sa.Column("prize_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("prize_title", sa.String(200), nullable=True),
        sa.Column("prize_category", sa.String(80), nullable=True),
        sa.Column("prize_worth", sa.String(80), nullable=True),
        sa.Column("redemption_instructions", sa.Text(), nullable=True),
        sa.Column("is_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["form_id"], ["event_registration_forms.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ticket_number", name="uq_event_reg_ticket_number"),
    )
    op.create_index("ix_event_registration_submissions_form_id", "event_registration_submissions", ["form_id"])
    op.create_index("ix_event_registration_submissions_email", "event_registration_submissions", ["email"])
    op.create_index("ix_event_registration_submissions_enquiry_id", "event_registration_submissions", ["enquiry_id"])

    op.add_column("career_enquiries", sa.Column("event_name", sa.String(200), nullable=True))
    op.add_column("career_enquiries", sa.Column("ticket_number", sa.String(40), nullable=True))
    op.add_column("career_enquiries", sa.Column("prize_title", sa.String(200), nullable=True))
    op.add_column("career_enquiries", sa.Column("event_form_id", postgresql.UUID(as_uuid=False), nullable=True))
    op.create_index("ix_career_enquiries_event_form_id", "career_enquiries", ["event_form_id"])
    op.create_index("ix_career_enquiries_ticket_number", "career_enquiries", ["ticket_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_career_enquiries_ticket_number", table_name="career_enquiries")
    op.drop_index("ix_career_enquiries_event_form_id", table_name="career_enquiries")
    op.drop_column("career_enquiries", "event_form_id")
    op.drop_column("career_enquiries", "prize_title")
    op.drop_column("career_enquiries", "ticket_number")
    op.drop_column("career_enquiries", "event_name")

    op.drop_index("ix_event_registration_submissions_enquiry_id", table_name="event_registration_submissions")
    op.drop_index("ix_event_registration_submissions_email", table_name="event_registration_submissions")
    op.drop_index("ix_event_registration_submissions_form_id", table_name="event_registration_submissions")
    op.drop_table("event_registration_submissions")

    op.drop_index("ix_event_registration_prizes_form_id", table_name="event_registration_prizes")
    op.drop_table("event_registration_prizes")

    op.drop_index("ix_event_registration_forms_slug", table_name="event_registration_forms")
    op.drop_table("event_registration_forms")
