from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class SuperAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class SuperAdminLoginResponse(BaseModel):
    access_token: str
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


class AdminSeekerCreate(AdminUserBase):
    industry: Optional[str] = None
    job_role: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    experience: Optional[str] = None


class AdminSeekerUpdate(BaseModel):
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


class AdminProviderCreate(AdminUserBase):
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    company_location: Optional[str] = None
    company_size: Optional[str] = None


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
    phone: str
    role: str
    has_password: bool = False
    is_verified: bool
    onboarding_complete: bool
    industry: Optional[str] = None
    job_role: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    experience: Optional[str] = None
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    company_location: Optional[str] = None
    company_size: Optional[str] = None
    profile_completion_percentage: Optional[int] = None
    welcome_email_status: Optional[str] = None
    welcome_email_error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    items: List[AdminUserOut]
    total: int
    page: int
    page_size: int


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
    seeker_name: str
    seeker_email: Optional[str] = None
    job_title: Optional[str] = None
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
