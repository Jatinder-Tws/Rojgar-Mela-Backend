from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat() + "Z"


class SiteAnnouncementCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    text: str = Field(..., min_length=2)
    category: str = Field("announcement", max_length=50)
    display_placement: str = Field("top_banner", max_length=50)
    target_pages: str = Field("all", max_length=255)
    image_url: Optional[str] = Field(None)
    link_url: Optional[str] = Field(None, max_length=1000)
    link_text: Optional[str] = Field(None, max_length=100)
    event_date: Optional[datetime] = None
    event_location: Optional[str] = Field(None, max_length=255)
    organizer: Optional[str] = Field(None, max_length=255)
    home_layout: Optional[str] = Field(None, max_length=20)  # banner | card
    badge_label: Optional[str] = Field(None, max_length=80)
    tagline: Optional[str] = Field(None, max_length=255)
    show_content_on_image: bool = True
    gallery_images: Optional[List[str]] = Field(default_factory=list)
    qr_code_url: Optional[str] = None
    modal_delay_seconds: int = Field(5, ge=0, le=300)
    start_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    show_on_website: bool = True
    ticketing_enabled: bool = False
    lucky_draw_enabled: bool = False
    lucky_draw_slug: Optional[str] = Field(None, max_length=80)
    lucky_draw_days: int = Field(1, ge=1, le=30)
    lucky_draw_reveal_time: str = Field("18:00", max_length=5)
    sort_order: int = 0
    event_profile: Optional[dict] = None

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) < 2:
            raise ValueError("Message text is required")
        return cleaned

    @field_validator("link_url", "image_url", "title", "link_text", "event_location", "organizer", "badge_label", "tagline", "qr_code_url")
    @classmethod
    def strip_optional_str(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("gallery_images")
    @classmethod
    def clean_gallery_images(cls, value: Optional[List[str]]) -> List[str]:
        if not value:
            return []
        return [str(v).strip() for v in value if v and str(v).strip()]

    @field_validator("home_layout")
    @classmethod
    def clean_home_layout(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if cleaned not in ("banner", "card"):
            raise ValueError("Homepage layout must be banner or card")
        return cleaned

    @field_validator("event_date", "start_date", "expires_at", mode="after")
    @classmethod
    def strip_tzinfo(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


class SiteAnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    text: Optional[str] = Field(None, min_length=2)
    category: Optional[str] = Field(None, max_length=50)
    display_placement: Optional[str] = Field(None, max_length=50)
    target_pages: Optional[str] = Field(None, max_length=255)
    image_url: Optional[str] = None
    link_url: Optional[str] = Field(None, max_length=1000)
    link_text: Optional[str] = Field(None, max_length=100)
    event_date: Optional[datetime] = None
    event_location: Optional[str] = Field(None, max_length=255)
    organizer: Optional[str] = Field(None, max_length=255)
    home_layout: Optional[str] = Field(None, max_length=20)
    badge_label: Optional[str] = Field(None, max_length=80)
    tagline: Optional[str] = Field(None, max_length=255)
    show_content_on_image: Optional[bool] = None
    gallery_images: Optional[List[str]] = None
    qr_code_url: Optional[str] = None
    modal_delay_seconds: Optional[int] = Field(None, ge=0, le=300)
    start_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    show_on_website: Optional[bool] = None
    ticketing_enabled: Optional[bool] = None
    lucky_draw_enabled: Optional[bool] = None
    lucky_draw_slug: Optional[str] = Field(None, max_length=80)
    lucky_draw_days: Optional[int] = Field(None, ge=1, le=30)
    lucky_draw_reveal_time: Optional[str] = Field(None, max_length=5)
    sort_order: Optional[int] = None
    event_profile: Optional[dict] = None

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Message text is required")
        return cleaned

    @field_validator("link_url", "image_url", "title", "link_text", "event_location", "organizer", "badge_label", "tagline", "qr_code_url")
    @classmethod
    def strip_optional_str(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("gallery_images")
    @classmethod
    def clean_gallery_images_update(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        return [str(v).strip() for v in value if v and str(v).strip()]

    @field_validator("home_layout")
    @classmethod
    def clean_home_layout(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if cleaned not in ("banner", "card"):
            raise ValueError("Homepage layout must be banner or card")
        return cleaned

    @field_validator("event_date", "start_date", "expires_at", mode="after")
    @classmethod
    def strip_tzinfo_update(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


class SiteAnnouncementOut(BaseModel):
    id: str
    title: Optional[str] = None
    text: str
    category: Optional[str] = "announcement"
    display_placement: Optional[str] = "top_banner"
    target_pages: Optional[str] = "all"
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    link_text: Optional[str] = None
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    organizer: Optional[str] = None
    home_layout: Optional[str] = None
    badge_label: Optional[str] = None
    tagline: Optional[str] = None
    show_content_on_image: Optional[bool] = True
    gallery_images: Optional[List[str]] = None
    qr_code_url: Optional[str] = None
    modal_delay_seconds: Optional[int] = 5
    start_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    show_on_website: Optional[bool] = True
    ticketing_enabled: Optional[bool] = False
    lucky_draw_enabled: Optional[bool] = False
    lucky_draw_slug: Optional[str] = None
    lucky_draw_days: Optional[int] = 1
    lucky_draw_reveal_time: Optional[str] = "18:00"
    sort_order: Optional[int] = 0
    event_profile: Optional[dict] = None
    registered_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "category",
        "display_placement",
        "target_pages",
        "show_content_on_image",
        "modal_delay_seconds",
        "show_on_website",
        "lucky_draw_enabled",
        "lucky_draw_days",
        "lucky_draw_reveal_time",
        "sort_order",
        mode="before",
    )
    @classmethod
    def fallback_none(cls, v, info):
        if v is not None:
            return v
        defaults = {
            "category": "announcement",
            "display_placement": "top_banner",
            "target_pages": "all",
            "show_content_on_image": True,
            "modal_delay_seconds": 5,
            "show_on_website": True,
            "lucky_draw_enabled": False,
            "lucky_draw_days": 1,
            "lucky_draw_reveal_time": "18:00",
            "sort_order": 0,
        }
        return defaults.get(info.field_name)

    @field_serializer("created_at", "updated_at", "event_date", "start_date", "expires_at")
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class SiteAnnouncementPublicOut(BaseModel):
    id: str
    title: Optional[str] = None
    text: str
    category: Optional[str] = "announcement"
    display_placement: Optional[str] = "top_banner"
    target_pages: Optional[str] = "all"
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    link_text: Optional[str] = None
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    organizer: Optional[str] = None
    home_layout: Optional[str] = None
    badge_label: Optional[str] = None
    tagline: Optional[str] = None
    show_content_on_image: Optional[bool] = True
    gallery_images: Optional[List[str]] = None
    qr_code_url: Optional[str] = None
    modal_delay_seconds: Optional[int] = 5
    expires_at: Optional[datetime] = None
    ticketing_enabled: Optional[bool] = False
    lucky_draw_enabled: Optional[bool] = False
    lucky_draw_slug: Optional[str] = None
    lucky_draw_days: Optional[int] = 1
    lucky_draw_reveal_time: Optional[str] = "18:00"
    start_date: Optional[datetime] = None
    event_profile: Optional[dict] = None

    @field_validator(
        "category",
        "display_placement",
        "target_pages",
        "show_content_on_image",
        "modal_delay_seconds",
        "lucky_draw_enabled",
        "lucky_draw_days",
        "lucky_draw_reveal_time",
        mode="before",
    )
    @classmethod
    def fallback_none_public(cls, v, info):
        if v is not None:
            return v
        defaults = {
            "category": "announcement",
            "display_placement": "top_banner",
            "target_pages": "all",
            "show_content_on_image": True,
            "modal_delay_seconds": 5,
            "lucky_draw_enabled": False,
            "lucky_draw_days": 1,
            "lucky_draw_reveal_time": "18:00",
        }
        return defaults.get(info.field_name)

    @field_serializer("event_date", "expires_at", "start_date")
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class SiteAnnouncementListResponse(BaseModel):
    items: List[SiteAnnouncementOut]
    total: int

