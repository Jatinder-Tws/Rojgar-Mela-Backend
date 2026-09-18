from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


def _utc_iso(dt: datetime) -> str:
    if dt is None:
        return ""
    return dt.isoformat() + "Z"


class SiteAnnouncementCreate(BaseModel):
    text: str = Field(..., min_length=2, max_length=280)
    link_url: Optional[str] = Field(None, max_length=500)
    is_active: bool = True
    sort_order: int = 0

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) < 2:
            raise ValueError("Announcement text is required")
        return cleaned

    @field_validator("link_url")
    @classmethod
    def strip_link(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SiteAnnouncementUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=2, max_length=280)
    link_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Announcement text is required")
        return cleaned

    @field_validator("link_url")
    @classmethod
    def strip_link(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class SiteAnnouncementOut(BaseModel):
    id: str
    text: str
    link_url: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class SiteAnnouncementPublicOut(BaseModel):
    id: str
    text: str
    link_url: Optional[str] = None

    class Config:
        from_attributes = True


class SiteAnnouncementListResponse(BaseModel):
    items: List[SiteAnnouncementOut]
    total: int
