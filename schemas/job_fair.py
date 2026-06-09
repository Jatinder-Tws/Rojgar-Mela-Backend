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

class JobFairOut(JobFairBase):
    id: str
    slug: str
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

    class Config:
        from_attributes = True


class JobFairListResponse(BaseModel):
    items: List[JobFairOut]
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

