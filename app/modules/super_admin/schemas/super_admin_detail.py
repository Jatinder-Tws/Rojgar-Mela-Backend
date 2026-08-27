"""
Schemas for super admin provider / seeker detail pages - enriched version.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ── Job (for listing under provider) ──────────────────────────────────────

class ProviderJobItem(BaseModel):
    id: str
    title: str
    industry: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    experience_required: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    is_active: bool
    posted_by_name: Optional[str] = None
    employment_type: Optional[str] = None
    shift: Optional[str] = None
    perks: Optional[List[str]] = None
    application_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Application (for listing under seeker) ────────────────────────────────

class SeekerApplicationItem(BaseModel):
    id: str
    job_title: str
    company_name: Optional[str] = None
    company_location: Optional[str] = None
    industry: Optional[str] = None
    status: str
    applied_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Interview item (for seeker) ───────────────────────────────────────────

class SeekerInterviewItem(BaseModel):
    id: str
    title: str
    job_title: Optional[str] = None
    provider_name: Optional[str] = None
    interview_type: Optional[str] = None
    status: str
    scheduled_at: datetime
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    interviewer_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Provider Interview item ───────────────────────────────────────────────

class ProviderInterviewItem(BaseModel):
    id: str
    title: str
    seeker_name: Optional[str] = None
    job_title: Optional[str] = None
    interview_type: Optional[str] = None
    status: str
    scheduled_at: datetime
    meeting_link: Optional[str] = None

    class Config:
        from_attributes = True


# ── Provider Detail ───────────────────────────────────────────────────────

class AdminProviderDetailResponse(BaseModel):
    # Identity
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_pic_url: Optional[str] = None
    role: str = "provider"

    # Account state
    has_password: bool = False
    is_verified: bool
    onboarding_complete: bool
    is_first_login: Optional[bool] = None
    welcome_email_status: Optional[str] = None
    welcome_email_error: Optional[str] = None

    # Company info
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    company_location: Optional[str] = None
    company_address: Optional[str] = None
    company_size: Optional[str] = None

    # Provider-specific fields
    gender: Optional[str] = None
    job_roles_offering: Optional[str] = None
    specific_requirements: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None

    # Provider job postings (detailed)
    job_postings: List[ProviderJobItem] = []
    total_jobs: int = 0
    active_jobs: int = 0
    total_applications_received: int = 0

    # Recent interviews
    interviews: List[ProviderInterviewItem] = []

    class Config:
        from_attributes = True


# ── Seeker portfolio snippets ─────────────────────────────────────────────

class SeekerSkillItem(BaseModel):
    name: str
    level: Optional[str] = None


class SeekerEducationItem(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    grade: Optional[str] = None


class SeekerExperienceItem(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: Optional[bool] = None


# ── Seeker Detail ─────────────────────────────────────────────────────────

class AdminSeekerDetailResponse(BaseModel):
    # Identity
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_pic_url: Optional[str] = None
    role: str = "seeker"

    # Account state
    has_password: bool = False
    is_verified: bool
    onboarding_complete: bool
    is_assessment_done: bool = False
    is_first_login: Optional[bool] = None
    auto_apply_enabled: bool = False
    welcome_email_status: Optional[str] = None
    welcome_email_error: Optional[str] = None

    # Seeker profile
    industry: Optional[str] = None
    job_role: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    experience: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    profile_completion_percentage: Optional[int] = None
    profile_sections_filled: int = 0
    profile_sections_total: int = 0
    has_resume: bool = False

    # Extended personal info
    father_or_mother_name: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    highest_qualification: Optional[str] = None
    stream_specialization: Optional[str] = None
    college_institute_name: Optional[str] = None
    preferred_job_sector: Optional[str] = None

    # Portfolio (real profile data)
    headline: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None
    total_experience_years: Optional[float] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    skills: List[SeekerSkillItem] = []
    education_history: List[SeekerEducationItem] = []
    work_experiences: List[SeekerExperienceItem] = []

    # Job fair participation
    registered_job_fairs: Optional[List[str]] = None

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None

    # Seeker applications
    applications: List[SeekerApplicationItem] = []
    total_applications: int = 0
    shortlisted_count: int = 0
    interviewing_count: int = 0
    selected_count: int = 0

    # Interviews
    interviews: List[SeekerInterviewItem] = []

    class Config:
        from_attributes = True