from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import date, datetime

class CompanyInternshipCreate(BaseModel):
    title: str
    description: str
    thumbnail_url: Optional[str] = None
    brochure_url: Optional[str] = None
    is_stipend: bool = False
    stipend_amount: Optional[str] = None
    duration: int
    duration_unit: str = "month"  # "week" or "month"
    state: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    apply_by: Optional[date] = None
    start_date: Optional[str] = None
    company_name: str
    who_can_apply: Optional[str] = None
    skills_required: Optional[List[str]] = []
    perks: Optional[List[str]] = []


class CompanyInternshipUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    brochure_url: Optional[str] = None
    is_stipend: Optional[bool] = None
    stipend_amount: Optional[str] = None
    duration: Optional[int] = None
    duration_unit: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    apply_by: Optional[date] = None
    start_date: Optional[str] = None
    company_name: Optional[str] = None
    who_can_apply: Optional[str] = None
    skills_required: Optional[List[str]] = None
    perks: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CompanyInternshipOut(BaseModel):
    id: str
    provider_id: str
    title: str
    description: str
    thumbnail_url: Optional[str] = None
    brochure_url: Optional[str] = None
    is_stipend: bool
    stipend_amount: Optional[str] = None
    duration: int
    duration_unit: str
    state: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    apply_by: Optional[date] = None
    start_date: Optional[str] = None
    company_name: str
    who_can_apply: Optional[str] = None
    skills_required: Optional[List[str]] = []
    perks: Optional[List[str]] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime
    applicant_count: Optional[int] = 0

    class Config:
        from_attributes = True


class CompanyInternshipListResponse(BaseModel):
    items: List[CompanyInternshipOut]
    total: int
    page: int
    page_size: int


class CompanyInternshipApplicationCreate(BaseModel):
    why_join: str
    career_goals: str
    why_consider: str


class CompanyInternshipApplicationOut(BaseModel):
    id: str
    internship_id: str
    seeker_id: str
    why_join: str
    career_goals: str
    why_consider: str
    resume_url: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CandidateDetailsOut(BaseModel):
    seeker_id: str
    first_name: str
    last_name: Optional[str] = None
    email: str
    phone: str


class CompanyInternshipApplicationDetailOut(BaseModel):
    id: str
    internship_id: str
    seeker_id: str
    why_join: str
    career_goals: str
    why_consider: str
    resume_url: str
    created_at: datetime
    candidate: CandidateDetailsOut

    class Config:
        from_attributes = True


class CompanyInternshipApplicationListResponse(BaseModel):
    items: List[CompanyInternshipApplicationDetailOut]
    total: int
    page: int
    page_size: int
