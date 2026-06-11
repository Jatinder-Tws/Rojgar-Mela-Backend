from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

class ExternalCandidateBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    state: Optional[str] = None
    city: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    sub_role: Optional[str] = None
    industries: Optional[List[str]] = None
    available_shift: Optional[str] = None
    total_experience: Optional[str] = None
    current_ctc: Optional[str] = None
    current_designation: Optional[str] = None
    
    source: Optional[str] = None
    resume_url: Optional[str] = None
    salary_slip_url: Optional[str] = None
    experience_letter_url: Optional[str] = None
    profile_picture_url: Optional[str] = None
    job_id: Optional[str] = None
    job_fair_id: Optional[str] = None
    job_fair_slug: Optional[str] = None

class ExternalCandidateCreate(ExternalCandidateBase):
    pass

class ExternalCandidateOut(ExternalCandidateBase):
    id: str
    status: str
    is_matched: bool = False
    applied_at: datetime

    class Config:
        from_attributes = True


class ExternalCandidateMatchOut(BaseModel):
    """AI match result between an external candidate and a job posting."""
    match_id: str
    candidate_id: str
    job_id: str
    job_title: str
    job_industry: Optional[str] = None
    job_location: Optional[str] = None
    job_experience_required: Optional[str] = None
    score: float
    highlights: List[str] = []
    gaps: List[str] = []
    fit_reason: str = ""
    created_at: datetime

    class Config:
        from_attributes = True
