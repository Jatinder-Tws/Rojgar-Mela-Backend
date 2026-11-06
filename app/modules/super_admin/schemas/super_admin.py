from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.jobs_portal.schemas.portfolio import (
    CertificationItem,
    EducationItem,
    LanguageItem,
    ProjectItem,
    SkillItem,
    WorkExperienceItem,
)


class SuperAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class SuperAdminLoginResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict


class PlatformStatsResponse(BaseModel):
    total_seekers: int
    total_providers: int
    total_jobs: int
    active_jobs: int
    total_applications: int
    verified_users: int
    new_users_last_30_days: int
    users_by_role: dict
    registrations_over_time: List[dict]
    applications_by_status: dict


class AdminUserBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    password: Optional[str] = Field(None, min_length=8)


class AdminSeekerProfileFields(BaseModel):
    """Portfolio and extended profile fields a seeker can fill, written by admin."""

    preferred_locations: Optional[List[str]] = None
    father_or_mother_name: Optional[str] = Field(None, max_length=200)
    gender: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    highest_qualification: Optional[str] = Field(None, max_length=200)
    stream_specialization: Optional[str] = Field(None, max_length=200)
    college_institute_name: Optional[str] = Field(None, max_length=255)
    preferred_job_sector: Optional[str] = Field(None, max_length=200)
    headline: Optional[str] = Field(None, max_length=200)
    bio: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    total_experience_years: Optional[float] = Field(None, ge=0, le=80)
    current_company: Optional[str] = Field(None, max_length=200)
    current_role: Optional[str] = Field(None, max_length=200)
    skills: Optional[List[SkillItem]] = None
    work_experiences: Optional[List[WorkExperienceItem]] = None
    education: Optional[List[EducationItem]] = None
    certifications: Optional[List[CertificationItem]] = None
    languages: Optional[List[LanguageItem]] = None
    projects: Optional[List[ProjectItem]] = None

    @field_validator(
        "father_or_mother_name",
        "gender",
        "address",
        "highest_qualification",
        "stream_specialization",
        "college_institute_name",
        "preferred_job_sector",
        "headline",
        "bio",
        "date_of_birth",
        "city",
        "state",
        "linkedin_url",
        "github_url",
        "website_url",
        "current_company",
        "current_role",
    )
    @classmethod
    def strip_optional_profile_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = v.strip()
        return text or None

    @field_validator("preferred_locations")
    @classmethod
    def clean_preferred_locations(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        cleaned: List[str] = []
        for item in v:
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text[:200])
            if len(cleaned) >= 5:
                break
        return cleaned


class AdminSeekerCreate(AdminUserBase, AdminSeekerProfileFields):
    last_name: Optional[str] = Field(None, max_length=50)
    industry: str = Field(..., min_length=1, max_length=100)
    job_role: str = Field(..., min_length=1, max_length=100)
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    experience: Optional[str] = None

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Industry Type is required")
        return v.strip()

    @field_validator("job_role")
    @classmethod
    def validate_job_role(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Job Role is required")
        return v.strip()


class AdminSeekerUpdate(AdminSeekerProfileFields):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    industry: Optional[str] = None
    job_role: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    experience: Optional[str] = None
    is_verified: Optional[bool] = None
    onboarding_complete: Optional[bool] = None

    @field_validator("industry", "job_role")
    @classmethod
    def validate_optional_text_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip() if v else None


class AdminProviderCreate(AdminUserBase):
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    company_location: Optional[str] = None
    company_size: Optional[str] = None
    company_address: Optional[str] = None
    company_website: Optional[str] = None
    company_about: Optional[str] = None
    industry: Optional[str] = None
    job_role: Optional[str] = None
    company_rating: Optional[float] = None
    company_review_count: Optional[int] = None
    company_reviews: Optional[list] = None
    company_rating_source: Optional[str] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None


class AdminProviderUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    company_location: Optional[str] = None
    company_size: Optional[str] = None
    company_address: Optional[str] = None
    company_website: Optional[str] = None
    company_about: Optional[str] = None
    industry: Optional[str] = None
    job_role: Optional[str] = None
    company_rating: Optional[float] = None
    company_review_count: Optional[int] = None
    company_reviews: Optional[list] = None
    company_rating_source: Optional[str] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    is_verified: Optional[bool] = None
    onboarding_complete: Optional[bool] = None


class AdminSetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)


class AdminUserOut(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    profile_pic_url: Optional[str] = None
    phone: Optional[str] = None
    role: str
    has_password: bool = False
    is_verified: bool
    onboarding_complete: bool
    industry: Optional[str] = None
    industries: List[str] = Field(default_factory=list)
    job_role: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    experience: Optional[str] = None
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    company_location: Optional[str] = None
    company_size: Optional[str] = None
    company_address: Optional[str] = None
    company_website: Optional[str] = None
    company_about: Optional[str] = None
    company_rating: Optional[float] = None
    company_review_count: Optional[int] = None
    company_reviews: Optional[list] = None
    company_rating_source: Optional[str] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    profile_completion_percentage: Optional[int] = None
    welcome_email_status: Optional[str] = None
    welcome_email_error: Optional[str] = None
    has_resume: Optional[bool] = None
    created_at: datetime
    last_active_at: Optional[datetime] = None
    registered_job_fairs: Optional[List[str]] = None

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    items: List[AdminUserOut]
    total: int
    page: int
    page_size: int


class AdminUserExportRequest(BaseModel):
    fields: List[str]
    format: str = "csv"  # csv | xlsx
    search: Optional[str] = None
    industry: Optional[str] = None
    status: Optional[str] = None
    job_fair_id: Optional[str] = None


class BulkImportResult(BaseModel):
    created: int
    failed: int
    errors: List[str]


class BulkImportJobStarted(BaseModel):
    job_id: str
    message: str = "Import started in background"


class ImportJobStatus(BaseModel):
    id: str
    role: str
    filename: str = ""
    status: str
    progress: int
    total: int
    processed: int
    created: int
    failed: int
    errors: List[str]
    email_sent: int = 0
    email_failed: int = 0
    email_logs: List[str] = []
    message: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProfileCompletionStats(BaseModel):
    complete_80_plus: int
    partial_50_to_79: int
    low_under_50: int


class HiringPipelineStats(BaseModel):
    total_applications: int
    applied: int
    shortlisted: int
    rejected: int
    interviews_scheduled: int
    ai_matches: int
    shortlisted_last_30_days: int


class ShortlistActivityItem(BaseModel):
    application_id: str
    seeker_id: Optional[str] = None
    seeker_name: str
    seeker_email: Optional[str] = None
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    provider_id: Optional[str] = None
    provider_name: str
    provider_email: Optional[str] = None
    status: str
    updated_at: Optional[str] = None


class ProviderShortlistRank(BaseModel):
    provider_id: str
    provider_name: str
    shortlist_count: int


class DetailedPlatformAnalytics(BaseModel):
    total_seekers: int
    total_providers: int
    seekers_onboarded: int
    seekers_with_portfolio: int
    seekers_without_portfolio: int
    profile_completion: ProfileCompletionStats
    hiring_pipeline: HiringPipelineStats
    applications_by_status: dict
    recent_shortlists: List[ShortlistActivityItem]
    top_providers_by_shortlists: List[ProviderShortlistRank]


class DashboardKpiItem(BaseModel):
    key: str
    label: str
    value: int
    trend: float


class DashboardSummaryMetric(BaseModel):
    label: str
    value: str
    trend: Optional[float] = None


class DashboardFunnelStage(BaseModel):
    stage: str
    count: int
    pct: float


class DashboardScoreBracket(BaseModel):
    range: str
    count: int
    pct: float


class DashboardIndustryMatch(BaseModel):
    industry: str
    avg_score: float
    count: int


class DashboardSkillGap(BaseModel):
    skill: str
    count: int
    pct: float


class DashboardAiStatCard(BaseModel):
    key: str
    label: str
    value: str
    trend: Optional[float] = None


class DashboardAiMatching(BaseModel):
    total_matches: int
    avg_score: float
    top_score: float
    above_90: int
    above_80: int
    above_70: int
    stat_cards: List[DashboardAiStatCard]
    score_distribution: List[DashboardScoreBracket]
    industry_analysis: List[DashboardIndustryMatch]
    skill_gaps: List[DashboardSkillGap]


class DashboardGrowthPoint(BaseModel):
    date: str
    count: int


class DashboardExperienceLevel(BaseModel):
    level: str
    count: int
    pct: float


class DashboardIndustryDist(BaseModel):
    industry: str
    count: int
    pct: float


class DashboardSkill(BaseModel):
    skill: str
    count: int


class DashboardRecruiter(BaseModel):
    name: str
    applications: int


class DashboardSeekerRow(BaseModel):
    name: str
    industry: str
    status: str
    created_at: Optional[str] = None


class DashboardJobRow(BaseModel):
    title: str
    company: str
    industry: str
    status: str
    created_at: Optional[str] = None


class DashboardApplicationRow(BaseModel):
    candidate: str
    job: str
    status: str
    applied_at: Optional[str] = None


class DashboardActivityItem(BaseModel):
    type: str
    message: str
    time: Optional[str] = None


class DashboardAlert(BaseModel):
    level: str
    message: str


class DashboardOverviewItem(BaseModel):
    label: str
    value: int
    trend: float


class SuperAdminProfileOut(BaseModel):
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: str
    profile_pic_url: Optional[str] = None
    role: str = "super_admin"
    is_super_admin: bool = True


class SuperAdminProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15)


class SuperAdminChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class AdminJobProviderOption(BaseModel):
    id: str
    company_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    industry: Optional[str] = None
    company_location: Optional[str] = None


class AdminJobProviderOptionsResponse(BaseModel):
    items: List[AdminJobProviderOption]
    total: int
    page: int
    page_size: int


class AdminJobCreate(BaseModel):
    """Create a job posting on behalf of an existing provider account."""

    provider_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    required_skills: Optional[List[str]] = None
    experience_required: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    industry: Optional[str] = None
    posted_by_name: Optional[str] = None
    location: Optional[str] = None
    post_count: Optional[str] = None
    ai_interview_enabled: Optional[bool] = False
    selection_threshold: Optional[int] = 70
    shift: Optional[str] = None
    employment_type: Optional[str] = None
    perks: Optional[List[str]] = None
    posting_details: Optional[dict] = None
    is_active: Optional[bool] = True

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Job title is required")
        return v

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Provider is required")
        return v


class AdminJobListItem(BaseModel):
    id: str
    provider_id: Optional[str] = None
    title: str
    company: str
    industry: Optional[str] = None
    location: Optional[str] = None
    post_count: int = 0
    application_count: int = 0
    is_active: bool
    created_at: datetime


class AdminJobDetailResponse(BaseModel):
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
    post_count: int = 0
    ai_interview_enabled: bool = False
    selection_threshold: int = 70
    shift: Optional[str] = None
    employment_type: Optional[str] = None
    perks: Optional[List[str]] = []
    posting_details: Optional[dict] = None
    source_platform: Optional[str] = None
    external_apply_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Provider / company
    company: str
    company_type: Optional[str] = None
    company_industry: Optional[str] = None
    company_about: Optional[str] = None
    provider_email: Optional[str] = None
    provider_phone: Optional[str] = None
    company_location: Optional[str] = None
    company_address: Optional[str] = None
    company_size: Optional[str] = None
    company_website: Optional[str] = None
    company_logo_url: Optional[str] = None
    # Application funnel
    application_count: int = 0
    applications_by_status: dict[str, int] = Field(default_factory=dict)
    match_count: int = 0


class AdminMatchListItem(BaseModel):
    id: str
    seeker_name: str
    seeker_email: Optional[str] = None
    seeker_id: Optional[str] = None
    job_id: Optional[str] = None
    provider_id: Optional[str] = None
    job_title: str
    company: str
    score: float
    created_at: datetime
    application_id: Optional[str] = None
    application_status: Optional[str] = None


class AdminApplicationListItem(BaseModel):
    id: str
    candidate_name: str
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    seeker_id: Optional[str] = None
    job_id: str
    provider_id: Optional[str] = None
    job_title: str
    company: str
    status: str
    applied_at: datetime
    updated_at: datetime


class AdminShortlistRequest(BaseModel):
    """Admin/supervisor shortlists a seeker for a provider job (on behalf of provider)."""
    seeker_id: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)


class AdminInterviewListItem(BaseModel):
    id: str
    title: str
    seeker_id: Optional[str] = None
    seeker_name: str
    provider_id: Optional[str] = None
    provider_name: str
    job_id: Optional[str] = None
    job_title: str
    scheduled_at: datetime
    source: str


class AdminAssessmentListItem(BaseModel):
    id: str
    user_name: str
    user_email: Optional[str] = None
    personality_type: Optional[str] = None
    iq_score: Optional[int] = None
    aptitude_score: Optional[int] = None
    status: str
    created_at: datetime


class AdminJobListResponse(BaseModel):
    items: List[AdminJobListItem]
    total: int
    page: int
    page_size: int


class AdminMatchListResponse(BaseModel):
    items: List[AdminMatchListItem]
    total: int
    page: int
    page_size: int


class AdminApplicationListResponse(BaseModel):
    items: List[AdminApplicationListItem]
    total: int
    page: int
    page_size: int


class AdminInterviewListResponse(BaseModel):
    items: List[AdminInterviewListItem]
    total: int
    page: int
    page_size: int


class AdminAssessmentListResponse(BaseModel):
    items: List[AdminAssessmentListItem]
    total: int
    page: int
    page_size: int


class DashboardAnalyticsResponse(BaseModel):
    generated_at: str
    reporting_period: dict = {}
    today_kpis: List[DashboardKpiItem]
    summary_columns: dict
    recruitment_funnel: List[DashboardFunnelStage]
    funnel_velocity: List[dict] = []
    funnel_highlight: Optional[str] = None
    ai_matching: DashboardAiMatching
    candidate_growth: dict
    provider_growth: dict = {}
    experience_breakdown: List[DashboardExperienceLevel]
    industry_distribution: List[DashboardIndustryDist]
    top_skills: List[DashboardSkill]
    active_recruiters: List[DashboardRecruiter]
    latest_seekers: List[DashboardSeekerRow]
    recent_jobs: List[DashboardJobRow]
    recent_applications: List[DashboardApplicationRow]
    recent_activity: List[DashboardActivityItem]
    system_alerts: List[DashboardAlert]
    platform_overview: List[DashboardOverviewItem]
