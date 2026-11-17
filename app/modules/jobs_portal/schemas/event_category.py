from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EventCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    key: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = ""
    icon_name: Optional[str] = "Sparkles"
    tag_color: Optional[str] = "#64748B"
    pill_bg: Optional[str] = "rgba(100, 116, 139, 0.1)"
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True


class EventCategoryCreate(EventCategoryBase):
    pass


class EventCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon_name: Optional[str] = None
    tag_color: Optional[str] = None
    pill_bg: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class EventCategoryOut(BaseModel):
    id: str
    key: str
    name: str
    description: Optional[str] = ""
    icon_name: str
    tag_color: str
    pill_bg: str
    is_active: bool
    is_builtin: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
