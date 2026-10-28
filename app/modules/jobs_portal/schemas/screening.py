"""Pydantic schemas for AI Resume Screening APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class ManualJDIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    education_requirements: Optional[str] = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Job title is required")
        return v


class ScreeningBatchCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    job_ids: List[str] = Field(default_factory=list)
    manual_jds: List[ManualJDIn] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Batch name is required")
        return v


class ScreeningJDOut(BaseModel):
    id: str
    job_id: Optional[str] = None
    is_manual: bool = False
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    education_requirements: Optional[str] = None

    class Config:
        from_attributes = True


class ScreeningBatchSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    current_stage: Optional[str] = None
    total_files: int = 0
    uploaded_count: int = 0
    parsed_count: int = 0
    matched_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    pending_review_count: int = 0
    progress_percent: float = 0.0
    job_titles: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScreeningFailedFileOut(BaseModel):
    id: str
    original_filename: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ScreeningBatchDetail(ScreeningBatchSummary):
    jds: List[ScreeningJDOut] = Field(default_factory=list)
    error_summary: Optional[str] = None
    limits_snapshot: Optional[dict] = None
    failed_files: List[ScreeningFailedFileOut] = Field(default_factory=list)


class ScreeningDashboardStats(BaseModel):
    total_batches: int = 0
    resumes_processed: int = 0
    awaiting_review: int = 0
    failed_files: int = 0


class ScreeningBatchListOut(BaseModel):
    items: List[ScreeningBatchSummary]
    total: int
    page: int
    page_size: int
    stats: ScreeningDashboardStats


class ScreeningUploadResult(BaseModel):
    id: str
    original_filename: str
    file_size: int
    status: str
    detected_file_type: Optional[str] = None
    duplicate: bool = False
    error_message: Optional[str] = None


class ScreeningUploadResponse(BaseModel):
    uploaded: List[ScreeningUploadResult]
    rejected: List[dict]
    batch: ScreeningBatchSummary


class ScreeningProgressOut(BaseModel):
    batch_id: str
    status: str
    current_stage: Optional[str] = None
    progress_percent: float = 0.0
    total_files: int = 0
    uploaded_count: int = 0
    parsed_count: int = 0
    matched_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    pending_count: int = 0
    error_summary: Optional[str] = None


class RecruiterDecisionIn(BaseModel):
    decision: str = Field(..., pattern="^(none|shortlisted|rejected|review)$")
    notes: Optional[str] = None


class BulkDecisionIn(BaseModel):
    match_ids: List[str] = Field(..., min_length=1)
    decision: str = Field(..., pattern="^(none|shortlisted|rejected|review)$")
    notes: Optional[str] = None


class MatchResultOut(BaseModel):
    match_id: str
    batch_resume_id: str
    screening_jd_id: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_location: Optional[str] = None
    experience_years: Optional[float] = None
    skills: List[Any] = Field(default_factory=list)
    overall_score: float = 0.0
    score_breakdown: Optional[dict] = None
    matched_requirements: List[Any] = Field(default_factory=list)
    partially_matched_requirements: List[Any] = Field(default_factory=list)
    missing_requirements: List[Any] = Field(default_factory=list)
    match_confidence: Optional[str] = None
    data_quality: Optional[str] = None
    matching_status: str = "pending"
    recruiter_decision: str = "none"
    fit_reason: Optional[str] = None
    original_filename: Optional[str] = None
    quality_status: Optional[str] = None


class MatchResultsPage(BaseModel):
    items: List[MatchResultOut]
    total: int
    page: int
    page_size: int
    jd: Optional[ScreeningJDOut] = None
    disclaimer: str = (
        "Match scores are decision-support estimates based on extracted resume evidence, "
        "not guarantees of candidate performance or hireability."
    )


class CandidateDetailOut(BaseModel):
    match: MatchResultOut
    profile: Optional[dict] = None
    evidence: Optional[Any] = None
    recruiter_notes: Optional[str] = None
    resume_download_available: bool = False
    extraction: Optional[dict] = None


class ReportCreateIn(BaseModel):
    report_type: str = Field(..., pattern="^(csv|xlsx|pdf)$")


class ReportOut(BaseModel):
    id: str
    batch_id: str
    report_type: str
    status: str
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScreeningLimitsOut(BaseModel):
    max_resumes_per_batch: int
    max_concurrent_batches: int
    max_file_size_mb: int
    accepted_types: List[str]
    monthly_resume_limit: Optional[int] = None
    monthly_resumes_used: int = 0
