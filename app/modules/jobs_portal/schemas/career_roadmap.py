from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


def coerce_label_text(value: Any, max_len: int = 80) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("Value must be text")
    if isinstance(value, (int, float)):
        number = int(value) if float(value) == int(value) else value
        return str(number)
    text = " ".join(str(value).split())
    if not text:
        return None
    if len(text) > max_len:
        raise ValueError(f"Must be {max_len} characters or fewer")
    return text


class RoadmapLessonIn(BaseModel):
    id: Optional[str] = None
    title: str = ""


class RoadmapResourceIn(BaseModel):
    id: Optional[str] = None
    title: str = ""
    type: str = Field("article", max_length=40)
    url: str = ""
    platform: Optional[str] = Field(None, max_length=100)
    is_free: bool = True


class RoadmapSubStepIn(BaseModel):
    id: Optional[str] = None
    title: str = ""
    subtitle: str = ""
    duration: Optional[str] = Field(None, max_length=80)
    level: Optional[str] = Field(None, max_length=50)
    skill_tags: list[str] = Field(default_factory=list)
    resources: list[RoadmapResourceIn] = Field(default_factory=list)

    @field_validator("duration", "level", mode="before")
    @classmethod
    def _coerce_optional_label(cls, value: Any) -> Optional[str]:
        return coerce_label_text(value)


class RoadmapStepIn(BaseModel):
    id: Optional[str] = None
    title: str = ""
    content: str = ""
    duration: Optional[str] = Field(None, max_length=80)
    lessons_count: int = 0
    projects_count: int = 0
    quizzes_count: int = 0
    lessons: list[RoadmapLessonIn] = Field(default_factory=list)
    sub_steps: list[RoadmapSubStepIn] = Field(default_factory=list)

    @field_validator("duration", mode="before")
    @classmethod
    def _coerce_duration(cls, value: Any) -> Optional[str]:
        return coerce_label_text(value)


class CareerInsightsIn(BaseModel):
    top_hiring_companies: list[str] = Field(default_factory=list)
    in_demand_skills: list[str] = Field(default_factory=list)
    related_career_paths: list[str] = Field(default_factory=list)


class RoadmapFaqIn(BaseModel):
    id: Optional[str] = None
    question: str = ""
    answer: str = ""


class CareerRoadmapBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: Optional[str] = Field(None, max_length=200)
    category: str = Field("Technology", max_length=100)
    level: str = Field("Intermediate", max_length=50)
    industries: list[str] = Field(default_factory=list)
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    skill_tags: list[str] = Field(default_factory=list)
    duration_months: Optional[str] = Field(None, max_length=80)
    salary_lpa: Optional[str] = Field(None, max_length=80)
    growth_percent: Optional[str] = Field(None, max_length=80)
    openings_count: Optional[str] = Field(None, max_length=80)
    steps: list[RoadmapStepIn] = Field(default_factory=list)
    resources: list[RoadmapResourceIn] = Field(default_factory=list)
    career_insights: CareerInsightsIn = Field(default_factory=CareerInsightsIn)
    faqs: list[RoadmapFaqIn] = Field(default_factory=list)
    hero_image_url: Optional[str] = None
    is_published: bool = False
    is_featured: bool = False
    is_trending: bool = False
    sort_order: int = 0

    @field_validator("duration_months", "salary_lpa", "growth_percent", "openings_count", mode="before")
    @classmethod
    def _coerce_overview_labels(cls, value: Any) -> Optional[str]:
        return coerce_label_text(value)


class CareerRoadmapCreate(CareerRoadmapBase):
    pass


class CareerRoadmapUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    level: Optional[str] = Field(None, max_length=50)
    industries: Optional[list[str]] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    skill_tags: Optional[list[str]] = None
    duration_months: Optional[str] = Field(None, max_length=80)
    salary_lpa: Optional[str] = Field(None, max_length=80)
    growth_percent: Optional[str] = Field(None, max_length=80)
    openings_count: Optional[str] = Field(None, max_length=80)
    steps: Optional[list[RoadmapStepIn]] = None
    resources: Optional[list[RoadmapResourceIn]] = None
    career_insights: Optional[CareerInsightsIn] = None
    faqs: Optional[list[RoadmapFaqIn]] = None
    hero_image_url: Optional[str] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_trending: Optional[bool] = None
    sort_order: Optional[int] = None

    @field_validator("duration_months", "salary_lpa", "growth_percent", "openings_count", mode="before")
    @classmethod
    def _coerce_overview_labels(cls, value: Any) -> Optional[str]:
        return coerce_label_text(value)


class RoadmapLessonOut(BaseModel):
    id: str
    title: str


class RoadmapResourceOut(BaseModel):
    id: str
    title: str
    type: str = "article"
    url: str = ""
    platform: Optional[str] = None
    is_free: bool = True


class RoadmapSubStepOut(BaseModel):
    id: str
    title: str
    subtitle: str = ""
    duration: Optional[str] = None
    level: Optional[str] = None
    skill_tags: list[str] = Field(default_factory=list)
    resources: list[RoadmapResourceOut] = Field(default_factory=list)


class RoadmapStepOut(BaseModel):
    id: str
    title: str
    content: str
    duration: Optional[str] = None
    lessons_count: int = 0
    projects_count: int = 0
    quizzes_count: int = 0
    lessons: list[RoadmapLessonOut] = Field(default_factory=list)
    sub_steps: list[RoadmapSubStepOut] = Field(default_factory=list)


class CareerInsightsOut(BaseModel):
    top_hiring_companies: list[str] = Field(default_factory=list)
    in_demand_skills: list[str] = Field(default_factory=list)
    related_career_paths: list[str] = Field(default_factory=list)


class RoadmapFaqOut(BaseModel):
    id: str
    question: str
    answer: str


class CareerRoadmapOut(BaseModel):
    id: str
    title: str
    slug: str
    category: str
    level: str
    industries: list[str] = Field(default_factory=list)
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    skill_tags: list[str] = Field(default_factory=list)
    duration_months: Optional[str] = None
    salary_lpa: Optional[str] = None
    growth_percent: Optional[str] = None
    openings_count: Optional[str] = None
    steps: list[RoadmapStepOut] = Field(default_factory=list)
    resources: list[RoadmapResourceOut] = Field(default_factory=list)
    career_insights: CareerInsightsOut = Field(default_factory=CareerInsightsOut)
    faqs: list[RoadmapFaqOut] = Field(default_factory=list)
    hero_image_url: Optional[str] = None
    is_published: bool
    is_featured: bool
    is_trending: bool
    sort_order: int = 0
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("duration_months", "salary_lpa", "growth_percent", "openings_count", mode="before")
    @classmethod
    def _coerce_overview_labels(cls, value: Any) -> Optional[str]:
        return coerce_label_text(value)

    class Config:
        from_attributes = True


class CareerRoadmapListItem(BaseModel):
    id: str
    title: str
    slug: str
    category: str
    level: str
    short_description: Optional[str] = None
    duration_months: Optional[str] = None
    salary_lpa: Optional[str] = None
    openings_count: Optional[str] = None
    steps_count: int = 0
    is_published: bool
    is_featured: bool
    is_trending: bool
    hero_image_url: Optional[str] = None
    updated_at: datetime

    @field_validator("duration_months", "salary_lpa", "openings_count", mode="before")
    @classmethod
    def _coerce_overview_labels(cls, value: Any) -> Optional[str]:
        return coerce_label_text(value)


class CareerRoadmapListResponse(BaseModel):
    items: list[CareerRoadmapListItem]
    total: int
    page: int
    page_size: int


class CareerRoadmapPublicListResponse(BaseModel):
    items: list[CareerRoadmapOut]
    total: int
    page: int
    page_size: int


class CareerRoadmapImageUploadResponse(BaseModel):
    url: str
