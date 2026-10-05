"""Add provider company profile fields and gallery images.

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-09-16 15:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

from migrations.helpers import (
    add_column_if_missing,
    create_index_if_missing,
    drop_column_if_exists,
    drop_index_if_exists,
    drop_table_if_exists,
    table_exists,
)


revision = "e6f7a8b9c0d1"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column_if_missing("users", sa.Column("company_website", sa.String(length=500), nullable=True))
    add_column_if_missing("users", sa.Column("company_about", sa.Text(), nullable=True))
    add_column_if_missing("users", sa.Column("company_rating", sa.Float(), nullable=True))
    add_column_if_missing("users", sa.Column("company_review_count", sa.Integer(), nullable=True))
    add_column_if_missing("users", sa.Column("company_reviews", sa.JSON(), nullable=True))
    add_column_if_missing("users", sa.Column("company_rating_source", sa.String(length=20), nullable=True))
    add_column_if_missing("users", sa.Column("google_place_id", sa.String(length=128), nullable=True))
    add_column_if_missing("users", sa.Column("google_maps_url", sa.Text(), nullable=True))

    if not table_exists("company_gallery_images"):
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
    create_index_if_missing(
        "ix_company_gallery_images_provider_id",
        "company_gallery_images",
        ["provider_id"],
    )


def downgrade() -> None:
    drop_index_if_exists("ix_company_gallery_images_provider_id", "company_gallery_images")
    drop_table_if_exists("company_gallery_images")
    for col in (
        "google_maps_url",
        "google_place_id",
        "company_rating_source",
        "company_reviews",
        "company_review_count",
        "company_rating",
        "company_about",
        "company_website",
    ):
        drop_column_if_exists("users", col)
