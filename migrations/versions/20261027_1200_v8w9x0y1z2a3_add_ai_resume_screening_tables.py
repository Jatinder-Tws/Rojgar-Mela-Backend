"""add ai resume screening tables

Revision ID: v8w9x0y1z2a3
Revises: u7v8w9x0y1z2
Create Date: 2026-10-27 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.helpers import drop_table_if_exists, table_exists

revision: str = "v8w9x0y1z2a3"
down_revision: Union[str, None] = "u7v8w9x0y1z2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not table_exists("screening_batches"):
        op.create_table(
            "screening_batches",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("provider_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
            sa.Column("current_stage", sa.String(40), nullable=True),
            sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("uploaded_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("parsed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("matched_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("pending_review_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("progress_percent", sa.Float(), nullable=False, server_default="0"),
            sa.Column("error_summary", sa.Text(), nullable=True),
            sa.Column("limits_snapshot", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_screening_batches_provider_id", "screening_batches", ["provider_id"])
        op.create_index("ix_screening_batches_created_by", "screening_batches", ["created_by"])
        op.create_index("ix_screening_batches_status", "screening_batches", ["status"])
        op.create_index("ix_screening_batches_created_at", "screening_batches", ["created_at"])

    if not table_exists("screening_batch_resumes"):
        op.create_table(
            "screening_batch_resumes",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("batch_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("screening_batches.id", ondelete="CASCADE"), nullable=False),
            sa.Column("storage_key", sa.String(500), nullable=False),
            sa.Column("original_filename", sa.String(255), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("detected_file_type", sa.String(50), nullable=True),
            sa.Column("content_checksum", sa.String(64), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="uploaded"),
            sa.Column("extraction_status", sa.String(40), nullable=True),
            sa.Column("error_code", sa.String(80), nullable=True),
            sa.Column("error_message", sa.String(500), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("extraction_version", sa.String(40), nullable=True),
            sa.Column("idempotency_key", sa.String(100), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("parsed_at", sa.DateTime(), nullable=True),
            sa.Column("matched_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("batch_id", "content_checksum", name="uq_screening_batch_checksum"),
        )
        op.create_index("ix_screening_batch_resumes_batch_id", "screening_batch_resumes", ["batch_id"])
        op.create_index("ix_screening_batch_resumes_content_checksum", "screening_batch_resumes", ["content_checksum"])
        op.create_index("ix_screening_batch_resumes_status", "screening_batch_resumes", ["status"])
        op.create_index("ix_screening_batch_resumes_idempotency_key", "screening_batch_resumes", ["idempotency_key"])
        op.create_index("ix_screening_batch_resumes_batch_status", "screening_batch_resumes", ["batch_id", "status"])

    if not table_exists("screening_resume_profiles"):
        op.create_table(
            "screening_resume_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("batch_resume_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("screening_batch_resumes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("schema_version", sa.String(20), nullable=False, server_default="1.0"),
            sa.Column("extraction_method", sa.String(60), nullable=True),
            sa.Column("quality_status", sa.String(40), nullable=True),
            sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("parser_version", sa.String(40), nullable=True),
            sa.Column("candidate_name", sa.String(200), nullable=True),
            sa.Column("candidate_email", sa.String(200), nullable=True),
            sa.Column("candidate_phone", sa.String(40), nullable=True),
            sa.Column("candidate_location", sa.String(200), nullable=True),
            sa.Column("experience_years", sa.Float(), nullable=True),
            sa.Column("skills", sa.JSON(), nullable=True),
            sa.Column("experience", sa.JSON(), nullable=True),
            sa.Column("education", sa.JSON(), nullable=True),
            sa.Column("projects", sa.JSON(), nullable=True),
            sa.Column("certifications", sa.JSON(), nullable=True),
            sa.Column("profile_json", sa.JSON(), nullable=True),
            sa.Column("raw_text_excerpt", sa.Text(), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("batch_resume_id", name="uq_screening_profile_resume"),
        )
        op.create_index("ix_screening_resume_profiles_batch_resume_id", "screening_resume_profiles", ["batch_resume_id"])
        op.create_index("ix_screening_resume_profiles_candidate_name", "screening_resume_profiles", ["candidate_name"])

    if not table_exists("screening_jds"):
        op.create_table(
            "screening_jds",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("batch_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("screening_batches.id", ondelete="CASCADE"), nullable=False),
            sa.Column("job_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True),
            sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("location", sa.String(200), nullable=True),
            sa.Column("employment_type", sa.String(40), nullable=True),
            sa.Column("required_skills", sa.JSON(), nullable=True),
            sa.Column("preferred_skills", sa.JSON(), nullable=True),
            sa.Column("min_experience_years", sa.Float(), nullable=True),
            sa.Column("max_experience_years", sa.Float(), nullable=True),
            sa.Column("education_requirements", sa.Text(), nullable=True),
            sa.Column("normalized_required_skills", sa.JSON(), nullable=True),
            sa.Column("normalized_preferred_skills", sa.JSON(), nullable=True),
            sa.Column("jd_version", sa.String(40), nullable=False, server_default="1"),
            sa.Column("normalization_meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_screening_jds_batch_id", "screening_jds", ["batch_id"])
        op.create_index("ix_screening_jds_job_id", "screening_jds", ["job_id"])

    if not table_exists("screening_candidate_matches"):
        op.create_table(
            "screening_candidate_matches",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("batch_resume_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("screening_batch_resumes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("screening_jd_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("screening_jds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("score_breakdown", sa.JSON(), nullable=True),
            sa.Column("matched_requirements", sa.JSON(), nullable=True),
            sa.Column("partially_matched_requirements", sa.JSON(), nullable=True),
            sa.Column("missing_requirements", sa.JSON(), nullable=True),
            sa.Column("relevant_evidence", sa.JSON(), nullable=True),
            sa.Column("match_confidence", sa.String(40), nullable=True),
            sa.Column("data_quality", sa.String(40), nullable=True),
            sa.Column("scoring_version", sa.String(40), nullable=False, server_default="1.0"),
            sa.Column("matching_status", sa.String(40), nullable=False, server_default="pending"),
            sa.Column("fit_reason", sa.Text(), nullable=True),
            sa.Column("recruiter_decision", sa.String(40), nullable=False, server_default="none"),
            sa.Column("recruiter_notes", sa.Text(), nullable=True),
            sa.Column("decision_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("decision_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("batch_resume_id", "screening_jd_id", name="uq_screening_resume_jd"),
        )
        op.create_index("ix_screening_candidate_matches_batch_resume_id", "screening_candidate_matches", ["batch_resume_id"])
        op.create_index("ix_screening_candidate_matches_screening_jd_id", "screening_candidate_matches", ["screening_jd_id"])
        op.create_index("ix_screening_candidate_matches_overall_score", "screening_candidate_matches", ["overall_score"])
        op.create_index("ix_screening_candidate_matches_matching_status", "screening_candidate_matches", ["matching_status"])
        op.create_index("ix_screening_candidate_matches_recruiter_decision", "screening_candidate_matches", ["recruiter_decision"])
        op.create_index("ix_screening_matches_jd_score", "screening_candidate_matches", ["screening_jd_id", "overall_score"])

    if not table_exists("screening_task_events"):
        op.create_table(
            "screening_task_events",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("batch_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("screening_batches.id", ondelete="CASCADE"), nullable=False),
            sa.Column("batch_resume_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("screening_batch_resumes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("event_type", sa.String(60), nullable=False),
            sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("error_class", sa.String(80), nullable=True),
            sa.Column("message", sa.String(500), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_screening_task_events_batch_id", "screening_task_events", ["batch_id"])
        op.create_index("ix_screening_task_events_batch_resume_id", "screening_task_events", ["batch_resume_id"])
        op.create_index("ix_screening_task_events_batch_created", "screening_task_events", ["batch_id", "created_at"])

    if not table_exists("screening_reports"):
        op.create_table(
            "screening_reports",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("batch_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("screening_batches.id", ondelete="CASCADE"), nullable=False),
            sa.Column("report_type", sa.String(20), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
            sa.Column("storage_key", sa.String(500), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.String(500), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_screening_reports_batch_id", "screening_reports", ["batch_id"])
        op.create_index("ix_screening_reports_status", "screening_reports", ["status"])


def downgrade() -> None:
    drop_table_if_exists("screening_reports")
    drop_table_if_exists("screening_task_events")
    drop_table_if_exists("screening_candidate_matches")
    drop_table_if_exists("screening_jds")
    drop_table_if_exists("screening_resume_profiles")
    drop_table_if_exists("screening_batch_resumes")
    drop_table_if_exists("screening_batches")
