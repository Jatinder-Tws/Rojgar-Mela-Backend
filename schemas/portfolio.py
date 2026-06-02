from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, field_validator


class SkillItem(BaseModel):
    name: str
    level: Optional[str] = None  # beginner, intermediate, advanced, expert


class WorkExperienceItem(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: bool = False


class EducationItem(BaseModel):
    institution: str
    degree: str
    field: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None


class CertificationItem(BaseModel):
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None


class LanguageItem(BaseModel):
    language: str
    proficiency: Optional[str] = None  # basic, conversational, fluent, native


class ProjectItem(BaseModel):
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    technologies: Optional[List[str]] = None


class PortfolioUpdate(BaseModel):
    headline: Optional[str] = None
    bio: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None

    total_experience_years: Optional[float] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None

    # User fields bridged to portfolio
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

    skills: Optional[List[SkillItem]] = None
    work_experiences: Optional[List[WorkExperienceItem]] = None
    education: Optional[List[EducationItem]] = None
    certifications: Optional[List[CertificationItem]] = None
    languages: Optional[List[LanguageItem]] = None
    projects: Optional[List[ProjectItem]] = None


class PortfolioOut(BaseModel):
    id: str
    user_id: str

    headline: Optional[str] = None
    bio: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None

    total_experience_years: Optional[float] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None

    # User fields bridged to portfolio
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    profile_pic_url: Optional[str] = None

    skills: Optional[List[SkillItem]] = None
    work_experiences: Optional[List[WorkExperienceItem]] = None
    education: Optional[List[EducationItem]] = None
    certifications: Optional[List[CertificationItem]] = None
    languages: Optional[List[LanguageItem]] = None
    projects: Optional[List[ProjectItem]] = None

    intro_video_filename: Optional[str] = None
    intro_audio_filename: Optional[str] = None
    has_intro_video: bool = False
    has_intro_audio: bool = False

    completion_percentage: int = 0

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioCompletionOut(BaseModel):
    percentage: int
    filled_sections: List[str]
    missing_sections: List[str]
