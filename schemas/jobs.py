from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, field_validator


class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: Optional[List[str]] = []
    experience_required: Optional[str] = None
    job_type: Optional[str] = None  # "in_office" | "wfh" | "hybrid"
    salary_range: Optional[str] = None
    industry: Optional[str] = None
    posted_by_name: Optional[str] = None
    location: Optional[str] = None
    post_count: Optional[str] = None
    ai_interview_enabled: Optional[bool] = False
    selection_threshold: Optional[int] = 70
    shift: Optional[str] = None
    employment_type: Optional[str] = None
    perks: Optional[List[str]] = []


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    experience_required: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    is_active: Optional[bool] = None
    location: Optional[str] = None
    post_count: Optional[int] = None
    ai_interview_enabled: Optional[bool] = None
    selection_threshold: Optional[int] = None
    shift: Optional[str] = None
    employment_type: Optional[str] = None
    perks: Optional[List[str]] = None


class JobOut(BaseModel):
    id: str
    provider_id: str
    title: str
    description: str
    required_skills: Optional[List[str]] = []
    experience_required: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    industry: Optional[str] = None
    posted_by_name: Optional[str] = None
    location: Optional[str] = None
    is_active: bool
    created_at: datetime
    post_count: int
    ai_interview_enabled: bool
    selection_threshold: int
    shift: Optional[str] = None
    employment_type: Optional[str] = None
    perks: Optional[List[str]] = []

    @field_validator("perks", "required_skills", mode="before")
    @classmethod
    def parse_json(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except Exception:
                return []
        return v

    class Config:
        from_attributes = True


class JobWithMatch(JobOut):
    match_score: Optional[float] = None
    fit_reason: Optional[str] = None
    highlights: Optional[List[str]] = None
    gaps: Optional[List[str]] = None


class ResumeOut(BaseModel):
    id: str
    user_id: str
    filename: str
    parsed_json: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeProcessingStatusOut(BaseModel):
    has_resume: bool
    resume_id: Optional[str] = None
    filename: Optional[str] = None
    processing_status: str = "idle"
    processing_message: Optional[str] = None
    ocr_used: bool = False
    profile_mapped: bool = False


class MatchedCandidateOut(BaseModel):
    match_id: str
    user_id: str
    first_name: str
    last_name: str
    email: str
    score: float
    highlights: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    fit_reason: Optional[str] = None
    resume_parsed_json: Optional[Any] = None
    resume_filename: Optional[str] = None
    profile_pic_url: Optional[str] = None


class ApplicationCreate(BaseModel):
    job_id: str


class ProviderShortlistRequest(BaseModel):
    seeker_id: str
    job_id: str


class RejectApplicationRequest(BaseModel):
    rejection_reason: str


class ApplicationOut(BaseModel):
    id: str
    seeker_id: Optional[str] = None
    job_id: str
    status: str
    rejection_reason: Optional[str] = None
    ai_feedback: Optional[Any] = None
    applied_at: datetime
    updated_at: datetime
    # Flattened job details for ease of use in frontend
    job_title: Optional[str] = None
    job_type: Optional[str] = None
    company_name: Optional[str] = None
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    job_description: Optional[str] = None
    required_skills: Optional[List[str]] = []
    location: Optional[str] = None
    ai_interview_enabled: Optional[bool] = False
    # Seeker details (populated for provider-facing endpoints)
    seeker_first_name: Optional[str] = None
    seeker_last_name: Optional[str] = None
    seeker_email: Optional[str] = None
    seeker_phone: Optional[str] = None
    seeker_profile_pic_url: Optional[str] = None
    # Guest details
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    candidate_experience: Optional[str] = None
    candidate_resume_url: Optional[str] = None
    candidate_job_category: Optional[str] = None
    candidate_job_role: Optional[str] = None
    candidate_job_location: Optional[str] = None
    candidate_journey: Optional[str] = None
    candidate_date_of_birth: Optional[str] = None
    candidate_gender: Optional[str] = None
    candidate_year_of_passing: Optional[str] = None
    candidate_skills: Optional[str] = None

    class Config:
        from_attributes = True


class ShortlistedApplicationOut(BaseModel):
    id: str
    job_id: str
    seeker_id: Optional[str] = None
    status: str
    applied_at: datetime
    job_title: str
    seeker_first_name: str
    seeker_last_name: str
    seeker_email: str
    seeker_phone: Optional[str] = None
    seeker_profile_pic_url: Optional[str] = None
    has_interview: bool = False
    interview_id: Optional[str] = None
    interview_status: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    message: str
    is_read: bool
    related_job_id: Optional[str] = None
    related_user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobDescriptionRequest(BaseModel):
    title: str
    exp_min: Optional[str] = None
    exp_max: Optional[str] = None
    sal_min: Optional[str] = None
    sal_max: Optional[str] = None
    salary_range: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    employment_type: Optional[str] = None
    shift: Optional[str] = None
    required_skills: Optional[List[str]] = []
    perks: Optional[List[str]] = []


class JobTitleRequest(BaseModel):
    title: str
    exp_min: Optional[str] = None
    exp_max: Optional[str] = None


class JobDescriptionOnlyResponse(BaseModel):
    description_1: str
    description_2: str


class JobSkillsResponse(BaseModel):
    skills: List[str]


class ResumeImproveRequest(BaseModel):
    job_title: str
    job_description: str
    technologies: str
    user_id: str