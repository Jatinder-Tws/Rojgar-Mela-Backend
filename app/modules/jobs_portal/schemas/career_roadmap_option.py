from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

RoadmapOptionKind = Literal["category", "level", "industry", "resource_type", "skill_tag"]


class RoadmapOptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class RoadmapOptionUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class RoadmapOptionOut(BaseModel):
    id: str
    kind: str
    name: str
    sort_order: int = 0
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime


class RoadmapOptionListResponse(BaseModel):
    items: list[RoadmapOptionOut]
