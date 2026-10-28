"""AI-Powered Bulk Resume Screening models (provider-owned private batches)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ScreeningBatch(Base):
    __tablename__ = "screening_batches"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    provider_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    # draft | uploading | queued | processing | completed | failed | cancelled | partial
    status = Column(String(40), nullable=False, default="draft", index=True)
    current_stage = Column(String(40), nullable=True)  # upload|parse|extract|match|report|done

    total_files = Column(Integer, nullable=False, default=0)
    uploaded_count = Column(Integer, nullable=False, default=0)
    parsed_count = Column(Integer, nullable=False, default=0)
    matched_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    pending_review_count = Column(Integer, nullable=False, default=0)

    progress_percent = Column(Float, nullable=False, default=0.0)
    error_summary = Column(Text, nullable=True)
    limits_snapshot = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    resumes = relationship(
        "ScreeningBatchResume",
        back_populates="batch",
        cascade="all, delete-orphan",
    )
    jds = relationship(
        "ScreeningJD",
        back_populates="batch",
        cascade="all, delete-orphan",
    )
    reports = relationship(
        "ScreeningReport",
        back_populates="batch",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "ScreeningTaskEvent",
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class ScreeningBatchResume(Base):
    __tablename__ = "screening_batch_resumes"
    __table_args__ = (
        UniqueConstraint("batch_id", "content_checksum", name="uq_screening_batch_checksum"),
        Index("ix_screening_batch_resumes_batch_status", "batch_id", "status"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    batch_id = Column(
        UUID(as_uuid=False),
        ForeignKey("screening_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    detected_file_type = Column(String(50), nullable=True)
    content_checksum = Column(String(64), nullable=False, index=True)

    # pending | uploaded | parsing | extracted | matching | matched | failed | skipped | cancelled
    status = Column(String(40), nullable=False, default="uploaded", index=True)
    extraction_status = Column(String(40), nullable=True)
    error_code = Column(String(80), nullable=True)
    error_message = Column(String(500), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    extraction_version = Column(String(40), nullable=True)
    idempotency_key = Column(String(100), nullable=True, index=True)

    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    parsed_at = Column(DateTime, nullable=True)
    matched_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    batch = relationship("ScreeningBatch", back_populates="resumes")
    profile = relationship(
        "ScreeningResumeProfile",
        back_populates="batch_resume",
        uselist=False,
        cascade="all, delete-orphan",
    )
    matches = relationship(
        "ScreeningCandidateMatch",
        back_populates="batch_resume",
        cascade="all, delete-orphan",
    )


class ScreeningResumeProfile(Base):
    __tablename__ = "screening_resume_profiles"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    batch_resume_id = Column(
        UUID(as_uuid=False),
        ForeignKey("screening_batch_resumes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    schema_version = Column(String(20), nullable=False, default="1.0")
    extraction_method = Column(String(60), nullable=True)
    quality_status = Column(String(40), nullable=True)  # good | partial | poor | failed
    requires_review = Column(Boolean, nullable=False, default=False)
    parser_version = Column(String(40), nullable=True)

    candidate_name = Column(String(200), nullable=True, index=True)
    candidate_email = Column(String(200), nullable=True)
    candidate_phone = Column(String(40), nullable=True)
    candidate_location = Column(String(200), nullable=True)
    experience_years = Column(Float, nullable=True)

    skills = Column(JSON, nullable=True)
    experience = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    projects = Column(JSON, nullable=True)
    certifications = Column(JSON, nullable=True)
    profile_json = Column(JSON, nullable=True)
    raw_text_excerpt = Column(Text, nullable=True)  # truncated safe excerpt only
    evidence = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    batch_resume = relationship("ScreeningBatchResume", back_populates="profile")


class ScreeningJD(Base):
    __tablename__ = "screening_jds"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    batch_id = Column(
        UUID(as_uuid=False),
        ForeignKey("screening_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = Column(
        UUID(as_uuid=False),
        ForeignKey("job_postings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_manual = Column(Boolean, nullable=False, default=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    employment_type = Column(String(40), nullable=True)
    required_skills = Column(JSON, nullable=True)
    preferred_skills = Column(JSON, nullable=True)
    min_experience_years = Column(Float, nullable=True)
    max_experience_years = Column(Float, nullable=True)
    education_requirements = Column(Text, nullable=True)
    normalized_required_skills = Column(JSON, nullable=True)
    normalized_preferred_skills = Column(JSON, nullable=True)
    jd_version = Column(String(40), nullable=False, default="1")
    normalization_meta = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    batch = relationship("ScreeningBatch", back_populates="jds")
    matches = relationship(
        "ScreeningCandidateMatch",
        back_populates="screening_jd",
        cascade="all, delete-orphan",
    )


class ScreeningCandidateMatch(Base):
    __tablename__ = "screening_candidate_matches"
    __table_args__ = (
        UniqueConstraint("batch_resume_id", "screening_jd_id", name="uq_screening_resume_jd"),
        Index("ix_screening_matches_jd_score", "screening_jd_id", "overall_score"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    batch_resume_id = Column(
        UUID(as_uuid=False),
        ForeignKey("screening_batch_resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    screening_jd_id = Column(
        UUID(as_uuid=False),
        ForeignKey("screening_jds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_score = Column(Float, nullable=False, default=0.0, index=True)
    score_breakdown = Column(JSON, nullable=True)
    matched_requirements = Column(JSON, nullable=True)
    partially_matched_requirements = Column(JSON, nullable=True)
    missing_requirements = Column(JSON, nullable=True)
    relevant_evidence = Column(JSON, nullable=True)
    match_confidence = Column(String(40), nullable=True)  # high | medium | low
    data_quality = Column(String(40), nullable=True)
    scoring_version = Column(String(40), nullable=False, default="1.0")
    # pending | matched | failed | skipped
    matching_status = Column(String(40), nullable=False, default="pending", index=True)
    fit_reason = Column(Text, nullable=True)

    # none | shortlisted | rejected | review
    recruiter_decision = Column(String(40), nullable=False, default="none", index=True)
    recruiter_notes = Column(Text, nullable=True)
    decision_by = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    batch_resume = relationship("ScreeningBatchResume", back_populates="matches")
    screening_jd = relationship("ScreeningJD", back_populates="matches")


class ScreeningTaskEvent(Base):
    __tablename__ = "screening_task_events"
    __table_args__ = (
        Index("ix_screening_task_events_batch_created", "batch_id", "created_at"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    batch_id = Column(
        UUID(as_uuid=False),
        ForeignKey("screening_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_resume_id = Column(
        UUID(as_uuid=False),
        ForeignKey("screening_batch_resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(60), nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    error_class = Column(String(80), nullable=True)
    message = Column(String(500), nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("ScreeningBatch", back_populates="events")


class ScreeningReport(Base):
    __tablename__ = "screening_reports"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    batch_id = Column(
        UUID(as_uuid=False),
        ForeignKey("screening_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # csv | xlsx | pdf
    report_type = Column(String(20), nullable=False)
    # queued | generating | ready | failed
    status = Column(String(40), nullable=False, default="queued", index=True)
    storage_key = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    error_message = Column(String(500), nullable=True)
    created_by = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    batch = relationship("ScreeningBatch", back_populates="reports")
