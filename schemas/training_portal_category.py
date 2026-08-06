from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TrainingPortalCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class TrainingPortalCategoryUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class TrainingPortalCategoryOut(BaseModel):
    id: str
    name: str
    sort_order: int
    course_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
