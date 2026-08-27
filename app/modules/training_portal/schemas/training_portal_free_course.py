from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


FreeCourseStatus = Literal["draft", "published", "archived"]


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
    lessons: List[FreeCourseLessonOut] = []
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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FreeCourseImportIn(BaseModel):
    youtube_url: str = Field(..., min_length=8, max_length=500)
    title: Optional[str] = Field(None, max_length=300)


class FreeCourseUpdateIn(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    status: Optional[FreeCourseStatus] = None
    thumbnail_url: Optional[str] = None
