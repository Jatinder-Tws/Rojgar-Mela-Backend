from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


FreeCourseStatus = Literal["draft", "published", "archived"]
FreeCourseResourceCategory = Literal[
    "video",
    "github_repo",
    "book",
    "research_paper",
    "course",
    "guide",
    "pdf",
]


class FreeCourseResourceOut(BaseModel):
    id: str
    category: FreeCourseResourceCategory
    url: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class FreeCourseLessonOut(BaseModel):
    id: str
    youtube_video_id: str
    youtube_url: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    sort_order: int

    class Config:
        from_attributes = True


class FreeCourseOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    youtube_url: str
    playlist_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    channel_title: Optional[str] = None
    status: FreeCourseStatus
    lesson_count: int = 0
    resource_count: int = 0
    lessons: List[FreeCourseLessonOut] = []
    resources: List[FreeCourseResourceOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FreeCourseListItemOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    youtube_url: str
    playlist_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    channel_title: Optional[str] = None
    status: FreeCourseStatus
    lesson_count: int = 0
    resource_count: int = 0
    youtube_video_id: Optional[str] = None
    resource_category: Optional[FreeCourseResourceCategory] = None
    resource_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PublicFreeCourseListOut(BaseModel):
    items: List[FreeCourseListItemOut]
    total: int
    page: int
    page_size: int
    has_more: bool
    source_counts: Dict[str, int] = {}
    total_published: int = 0


class FreeCourseResourcePreviewIn(BaseModel):
    url: str = Field(..., min_length=8, max_length=700)
    category: Optional[FreeCourseResourceCategory] = None


class FreeCourseResourcePreviewOut(BaseModel):
    url: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category: FreeCourseResourceCategory
    is_youtube: bool = False
    youtube_video_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FreeCourseResourceCreateIn(BaseModel):
    url: str = Field(..., min_length=8, max_length=700)
    category: FreeCourseResourceCategory
    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None


class FreeCourseResourceUpdateIn(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    category: Optional[FreeCourseResourceCategory] = None
    sort_order: Optional[int] = None


class FreeCourseLessonImportIn(BaseModel):
    youtube_url: str = Field(..., min_length=8, max_length=500)
    title: Optional[str] = Field(None, max_length=300)


class FreeCourseImportIn(BaseModel):
    source: Literal["youtube", "github_repo", "book", "research_paper", "course", "guide", "pdf"] = "youtube"
    url: Optional[str] = Field(None, min_length=8, max_length=700)
    youtube_url: Optional[str] = Field(None, min_length=8, max_length=500)
    title: Optional[str] = Field(None, max_length=300)


class FreeCourseUpdateIn(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    status: Optional[FreeCourseStatus] = None
    thumbnail_url: Optional[str] = None
