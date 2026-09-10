from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


DeliveryMode = Literal["Offline", "Online", "Hybrid"]
CourseStatus = Literal["draft", "published", "archived"]
SkillLevel = Literal["Beginner", "Intermediate", "Advanced"]


class TrainingPortalCourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=100)
    duration: str = Field(..., min_length=1, max_length=50)
    delivery_mode: DeliveryMode = "Offline"
    status: CourseStatus = "draft"
    skill_level: SkillLevel = "Beginner"
    fee: float = Field(default=12000.0, ge=0)
    emi_fee: Optional[float] = Field(default=None, ge=0)
    thumbnail_url: Optional[str] = None
    prerequisites: Optional[str] = None
    key_highlights: Optional[List[str]] = []
    curriculum: Optional[list] = []


class TrainingPortalCourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    duration: Optional[str] = Field(None, min_length=1, max_length=50)
    delivery_mode: Optional[DeliveryMode] = None
    status: Optional[CourseStatus] = None
    skill_level: Optional[SkillLevel] = None
    fee: Optional[float] = Field(None, ge=0)
    emi_fee: Optional[float] = Field(None, ge=0)
    thumbnail_url: Optional[str] = None
    prerequisites: Optional[str] = None
    key_highlights: Optional[List[str]] = None
    curriculum: Optional[list] = None


class TrainingPortalCourseOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    duration: str
    delivery_mode: DeliveryMode
    status: CourseStatus
    skill_level: SkillLevel
    fee: float
    emi_fee: Optional[float] = None
    thumbnail_url: Optional[str] = None
    prerequisites: Optional[str] = None
    key_highlights: List[str] = []
    curriculum: List[dict] = []
    batches_count: int = 0
    enrollments_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PublicPaidCourseListOut(BaseModel):
    items: List[TrainingPortalCourseOut]
    total: int
    page: int
    page_size: int
    has_more: bool
    category_counts: Dict[str, int] = {}
    total_published: int = 0
