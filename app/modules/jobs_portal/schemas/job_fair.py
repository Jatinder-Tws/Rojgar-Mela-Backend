from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

class JobFairBase(BaseModel):
    title: str
    description: Optional[str] = None
    date: datetime
    location: str
    banner_image_url: Optional[str] = None
    is_active: bool = True

class JobFairCreate(JobFairBase):
    pass

class JobFairUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    banner_image_url: Optional[str] = None
    is_active: Optional[bool] = None
    industries: Optional[List[str]] = None

class JobFairOut(JobFairBase):
    id: str
    slug: str
    industries: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobFairCompanyOut(BaseModel):
    id: str
    job_fair_id: str
    provider_id: str
    department: Optional[str] = None
    sector: Optional[str] = None
    vacancy: Optional[str] = None
    registered_at: datetime
    # Provider profile details
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_pic_url: Optional[str] = None
    # Detailed company registration fields
    website: Optional[str] = None
    company_size: Optional[str] = None
    company_address: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_designation: Optional[str] = None
    contact_person_phone: Optional[str] = None
    openings: Optional[List[dict]] = None
    state: Optional[str] = None
    city: Optional[str] = None

    class Config:
        from_attributes = True

class JobFairSeekerOut(BaseModel):
    id: str
    job_fair_id: str
    seeker_id: str
    is_attending: bool
    registered_at: datetime
    # Seeker details
    seeker_first_name: Optional[str] = None
    seeker_last_name: Optional[str] = None
    seeker_email: Optional[str] = None
    seeker_phone: Optional[str] = None
    seeker_resume_url: Optional[str] = None
    seeker_gender: Optional[str] = None
    seeker_date_of_birth: Optional[str] = None
    seeker_state: Optional[str] = None
    seeker_city: Optional[str] = None
    seeker_sub_role: Optional[str] = None
    seeker_industries: Optional[List[str]] = None
    seeker_available_shift: Optional[str] = None
    seeker_total_experience: Optional[str] = None
    seeker_current_ctc: Optional[str] = None
    seeker_source: Optional[str] = None
    seeker_current_designation: Optional[str] = None
    seeker_profile_picture_url: Optional[str] = None

    class Config:
        from_attributes = True


class JobFairListResponse(BaseModel):
    items: List[JobFairOut]
    total: int
    page: int
    page_size: int


class JobFairCompanyPublicOut(BaseModel):
    id: str
    company_name: Optional[str] = None
    profile_pic_url: Optional[str] = None
    sector: Optional[str] = None
    vacancy: Optional[str] = None


class JobFairCompanyPublicListResponse(BaseModel):
    items: List[JobFairCompanyPublicOut]
    total: int
    page: int
    page_size: int


class JobFairCompanyListResponse(BaseModel):
    items: List[JobFairCompanyOut]
    total: int
    page: int
    page_size: int


class JobFairSeekerListResponse(BaseModel):
    items: List[JobFairSeekerOut]
    total: int
    page: int
    page_size: int


class JobFairCompanyLogoOut(BaseModel):
    company_name: Optional[str] = None
    logo_url: Optional[str] = None


class JobFairPublicOut(BaseModel):
    id: str
    slug: str
    title: str
    description: Optional[str] = None
    date: datetime
    location: str
    banner_image_url: Optional[str] = None
    is_active: bool = True
    industries: Optional[List[str]] = None
    status: str
    is_online: bool = False
    company_count: int = 0
    candidate_count: int = 0
    company_logos: List[JobFairCompanyLogoOut] = []


class JobFairPublicCatalogResponse(BaseModel):
    live: List[JobFairPublicOut]
    upcoming: List[JobFairPublicOut]
    concluded: List[JobFairPublicOut]
    total: int

