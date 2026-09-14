"""add source fields on job_postings for PGRKAM govt job sync

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-09-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("job_postings")}
    indexes = {idx["name"] for idx in inspector.get_indexes("job_postings")}
    uniques = {uc["name"] for uc in inspector.get_unique_constraints("job_postings")}

    if "source_platform" not in columns:
        op.add_column("job_postings", sa.Column("source_platform", sa.String(length=50), nullable=True))
    if "external_id" not in columns:
        op.add_column("job_postings", sa.Column("external_id", sa.String(length=150), nullable=True))
    if "source_metadata" not in columns:
        op.add_column("job_postings", sa.Column("source_metadata", sa.JSON(), nullable=True))

    if "ix_job_postings_source_platform" not in indexes:
        op.create_index("ix_job_postings_source_platform", "job_postings", ["source_platform"])
    if "ix_job_postings_external_id" not in indexes:
        op.create_index("ix_job_postings_external_id", "job_postings", ["external_id"])
    if "uq_job_source_external_id" not in uniques:
        op.create_unique_constraint(
            "uq_job_source_external_id",
            "job_postings",
            ["source_platform", "external_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("job_postings")}
    indexes = {idx["name"] for idx in inspector.get_indexes("job_postings")}
    uniques = {uc["name"] for uc in inspector.get_unique_constraints("job_postings")}

    if "uq_job_source_external_id" in uniques:
        op.drop_constraint("uq_job_source_external_id", "job_postings", type_="unique")
    if "ix_job_postings_external_id" in indexes:
        op.drop_index("ix_job_postings_external_id", table_name="job_postings")
    if "ix_job_postings_source_platform" in indexes:
        op.drop_index("ix_job_postings_source_platform", table_name="job_postings")
    if "source_metadata" in columns:
        op.drop_column("job_postings", "source_metadata")
    if "external_id" in columns:
        op.drop_column("job_postings", "external_id")
    if "source_platform" in columns:
        op.drop_column("job_postings", "source_platform")
