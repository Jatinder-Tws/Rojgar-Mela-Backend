from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class TrainingModuleTopicCreate(BaseModel):
    title: str
    order_index: int = 0

class TrainingModuleTopicOut(BaseModel):
    id: str
    module_id: str
    title: str
    order_index: int
    created_at: datetime

    class Config:
        from_attributes = True

class TrainingModuleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 0
    estimated_hours: Optional[float] = None
    topics: Optional[List[TrainingModuleTopicCreate]] = []

class TrainingModuleOut(BaseModel):
    id: str
    course_id: str
    title: str
    description: Optional[str] = None
    order_index: int
    estimated_hours: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    topics: List[TrainingModuleTopicOut] = []

    class Config:
        from_attributes = True

class TrainingCourseCreate(BaseModel):
    title: str
    description: str
    thumbnail_url: Optional[str] = None
    brochure_url: Optional[str] = None
    is_paid: bool = False
    price: Optional[str] = None
    duration: int
    duration_unit: str = "month"  # "week" or "month"
    skills_learned: Optional[List[str]] = []
    has_certificate: bool = True
    company_name: str
    state: Optional[str] = None
    city: Optional[str] = None
    modules: Optional[List[TrainingModuleCreate]] = []

class TrainingCourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    brochure_url: Optional[str] = None
    is_paid: Optional[bool] = None
    price: Optional[str] = None
    duration: Optional[int] = None
    duration_unit: Optional[str] = None
    skills_learned: Optional[List[str]] = None
    has_certificate: Optional[bool] = None
    company_name: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    is_active: Optional[bool] = None
    modules: Optional[List[TrainingModuleCreate]] = None

class TrainingCourseOut(BaseModel):
    id: str
    provider_id: str
    title: str
    description: str
    thumbnail_url: Optional[str] = None
    brochure_url: Optional[str] = None
    is_paid: bool
    price: Optional[str] = None
    duration: int
    duration_unit: str
    skills_learned: Optional[List[str]] = []
    has_certificate: bool
    company_name: str
    state: Optional[str] = None
    city: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    modules: List[TrainingModuleOut] = []
    applicant_count: Optional[int] = 0

    class Config:
        from_attributes = True

class TrainingCourseListResponse(BaseModel):
    items: List[TrainingCourseOut]
    total: int
    page: int
    page_size: int

class TrainingCourseApplicationCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    location: str

class TrainingCourseApplicationOut(BaseModel):
    id: str
    course_id: str
    seeker_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    location: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TrainingCourseApplicationDetailOut(BaseModel):
    id: str
    course_id: str
    seeker_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    location: str
    created_at: datetime
    course_title: Optional[str] = None
    course_company: Optional[str] = None

    class Config:
        from_attributes = True


class TrainingCourseApplicationListResponse(BaseModel):
    items: List[TrainingCourseApplicationDetailOut]
    total: int
    page: int
    page_size: int
