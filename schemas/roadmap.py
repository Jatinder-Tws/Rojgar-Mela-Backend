from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from models.roadmap import MilestoneStatus, ResourceType, DifficultyLevel


# Resource Schemas
class ResourceBase(BaseModel):
    title: str
    type: ResourceType
    url: Optional[str] = None
    platform: Optional[str] = None
    duration: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    description: Optional[str] = None
    is_free: bool = True
    rating: Optional[float] = None


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[ResourceType] = None
    url: Optional[str] = None
    platform: Optional[str] = None
    duration: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    description: Optional[str] = None
    is_free: Optional[bool] = None
    rating: Optional[float] = None


class ResourceOut(ResourceBase):
    id: str
    milestone_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Milestone Schemas
class MilestoneBase(BaseModel):
    title: str
    description: Optional[str] = None
    stage_title: Optional[str] = None
    stage_order: int = 1
    order_num: int
    skills: Optional[List[str]] = None
    estimated_time: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.intermediate # Added difficulty
    status: MilestoneStatus = MilestoneStatus.pending
    dependencies: Optional[List[str]] = None

# Category & Master Role Schemas
class RoadmapRoleBase(BaseModel):
    title: str
    description: Optional[str] = None
    level: str = "Intermediate"
    growth: Optional[str] = None
    salary_range: Optional[str] = None
    skills: Optional[List[str]] = None

class RoadmapRoleOut(RoadmapRoleBase):
    id: str
    category_id: str
    class Config:
        from_attributes = True

class RoadmapCategoryBase(BaseModel):
    name: str
    icon: Optional[str] = None
    description: Optional[str] = None

class RoadmapCategoryOut(RoadmapCategoryBase):
    id: str
    roles: List[RoadmapRoleOut] = []
    class Config:
        from_attributes = True


class MilestoneCreate(MilestoneBase):
    resources: Optional[List[ResourceCreate]] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_num: Optional[int] = None
    skills: Optional[List[str]] = None
    estimated_time: Optional[str] = None
    status: Optional[MilestoneStatus] = None
    dependencies: Optional[List[str]] = None


class MilestoneOut(MilestoneBase):
    id: str
    roadmap_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    resources: List[ResourceOut] = []

    class Config:
        from_attributes = True


# Roadmap Schemas
class RoadmapGenerateRequest(BaseModel):
    target_role: str = Field(..., description="Target job role")
    current_level: Optional[str] = Field(None, description="Current skill level")
    target_level: Optional[str] = Field(None, description="Target skill level")
    learning_preferences: Optional[dict] = Field(None, description="Learning preferences")
    time_commitment: Optional[str] = Field(None, description="Weekly time commitment")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on")
    current_skills: Optional[List[str]] = Field(None, description="Candidate's current skills")
    force_regenerate: bool = Field(False, description="Bypass cached roadmap and generate a fresh one")


class RoadmapBase(BaseModel):
    target_role: str
    current_level: str
    target_level: str
    skills_to_develop: Optional[List[str]] = None
    current_skills: Optional[List[str]] = None
    estimated_duration: Optional[str] = None
    market_based_salary: Optional[dict] = None


class RoadmapCreate(RoadmapBase):
    milestones: Optional[List[MilestoneCreate]] = None


class RoadmapUpdate(BaseModel):
    target_role: Optional[str] = None
    current_level: Optional[str] = None
    target_level: Optional[str] = None
    skills_to_develop: Optional[List[str]] = None
    estimated_duration: Optional[str] = None
    market_based_salary: Optional[dict] = None
    status: Optional[str] = None


class RoadmapOut(RoadmapBase):
    id: str
    user_id: str
    status: str
    ai_prompt_version: str
    generation_preferences: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    milestones: List[MilestoneOut] = []
    progress_percentage: Optional[float] = None

    class Config:
        from_attributes = True


class RoadmapSummary(BaseModel):
    id: str
    target_role: str
    current_level: str
    target_level: str
    estimated_duration: Optional[str] = None
    status: str
    progress_percentage: float
    total_milestones: int
    completed_milestones: int
    created_at: datetime

    class Config:
        from_attributes = True


class MilestoneStatusUpdate(BaseModel):
    status: MilestoneStatus


class RoadmapProgress(BaseModel):
    roadmap_id: str
    total_milestones: int
    completed_milestones: int
    in_progress_milestones: int
    pending_milestones: int
    progress_percentage: float
    estimated_completion_date: Optional[datetime] = None
