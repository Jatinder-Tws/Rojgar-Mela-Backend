import uuid 
import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, JSON, String, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from database import Base


class MilestoneStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class ResourceType(str, enum.Enum):
    course = "course"
    article = "article"
    video = "video"
    project = "project"
    certification = "certification"


class DifficultyLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


def _uuid():
    return str(uuid.uuid4())

class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    target_role = Column(String(100), nullable=False)
    current_level = Column(String(50), nullable=False)
    target_level = Column(String(50), nullable=False)
    skills_to_develop = Column(ARRAY(String), nullable=True)
    current_skills = Column(ARRAY(String), nullable=True)
    estimated_duration = Column(String(50), nullable=True)
    market_based_salary = Column(JSON, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    
    # AI generation metadata
    ai_prompt_version = Column(String(20), default="1.0", nullable=False)
    generation_preferences = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="roadmaps")
    milestones = relationship("Milestone", back_populates="roadmap", cascade="all, delete-orphan")



# import uuid
# import enum
# from datetime import datetime
# from typing import List, Optional
# from sqlalchemy import Boolean, Column, DateTime, Enum, Float, JSON, String, Text, ForeignKey, Integer
# from sqlalchemy.dialects.postgresql import UUID, ARRAY
# from sqlalchemy.orm import relationship

# from database import Base


# class MilestoneStatus(str, enum.Enum):
#     pending = "pending"
#     in_progress = "in_progress"
#     completed = "completed"


# class ResourceType(str, enum.Enum):
#     course = "course"
#     article = "article"
#     video = "video"
#     project = "project"
#     certification = "certification"


# class DifficultyLevel(str, enum.Enum):
#     beginner = "beginner"
#     intermediate = "intermediate"
#     advanced = "advanced"


# def _uuid():
#     return str(uuid.uuid4())


# class Roadmap(Base):
#     __tablename__ = "roadmaps"

#     id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
#     user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
#     target_role = Column(String(100), nullable=False)
#     current_level = Column(String(50), nullable=False)
#     target_level = Column(String(50), nullable=False)
#     skills_to_develop = Column(ARRAY(String), nullable=True)
#     estimated_duration = Column(String(50), nullable=True)
#     status = Column(String(20), default="active", nullable=False)
    
#     # AI generation metadata
#     ai_prompt_version = Column(String(20), default="1.0", nullable=False)
#     generation_preferences = Column(JSON, nullable=True)
    
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

#     # Relationships
#     user = relationship("User", back_populates="roadmaps")
#     milestones = relationship("Milestone", back_populates="roadmap", cascade="all, delete-orphan")


class RoadmapCategory(Base):
    __tablename__ = "roadmap_categories"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False, unique=True)
    icon = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    roles = relationship("RoadmapRole", back_populates="category", cascade="all, delete-orphan")

class RoadmapRole(Base):
    __tablename__ = "roadmap_roles"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    category_id = Column(UUID(as_uuid=False), ForeignKey("roadmap_categories.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(String(50), default="Intermediate")
    growth = Column(String(20), nullable=True)
    salary_range = Column(String(50), nullable=True)
    skills = Column(ARRAY(String), nullable=True)
    category = relationship("RoadmapCategory", back_populates="roles")

class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    roadmap_id = Column(UUID(as_uuid=False), ForeignKey("roadmaps.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    stage_title = Column(String(100), nullable=True)  # New field for grouping
    stage_order = Column(Integer, default=1)           # Order of the stage
    order_num = Column(Integer, nullable=False)        # Order within the roadmap or stage
    skills = Column(ARRAY(String), nullable=True)
    estimated_time = Column(String(50), nullable=True)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.intermediate) # Added difficulty
    status = Column(Enum(MilestoneStatus), default=MilestoneStatus.pending, nullable=False)
    dependencies = Column(ARRAY(UUID), nullable=True)  # milestone IDs
    
    # Progress tracking
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    roadmap = relationship("Roadmap", back_populates="milestones")
    resources = relationship("Resource", back_populates="milestone", cascade="all, delete-orphan")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    milestone_id = Column(UUID(as_uuid=False), ForeignKey("milestones.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    type = Column(Enum(ResourceType), nullable=False)
    url = Column(Text, nullable=True)
    platform = Column(String(100), nullable=True)
    duration = Column(String(50), nullable=True)
    difficulty = Column(Enum(DifficultyLevel), nullable=True)
    description = Column(Text, nullable=True)
    
    # Additional metadata
    is_free = Column(Boolean, default=True, nullable=False)
    rating = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    milestone = relationship("Milestone", back_populates="resources")
