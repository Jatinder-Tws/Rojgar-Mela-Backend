"""Add provider company profile fields and gallery images.

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-09-16 15:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e6f7a8b9c0d1"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("company_website", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("company_about", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("company_rating", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("company_review_count", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("company_reviews", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("company_rating_source", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("google_place_id", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("google_maps_url", sa.Text(), nullable=True))

    op.create_table(
        "company_gallery_images",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("provider_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("caption", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_company_gallery_images_provider_id",
        "company_gallery_images",
        ["provider_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_company_gallery_images_provider_id", table_name="company_gallery_images")
    op.drop_table("company_gallery_images")
    op.drop_column("users", "google_maps_url")
    op.drop_column("users", "google_place_id")
    op.drop_column("users", "company_rating_source")
    op.drop_column("users", "company_reviews")
    op.drop_column("users", "company_review_count")
    op.drop_column("users", "company_rating")
    op.drop_column("users", "company_about")
    op.drop_column("users", "company_website")
