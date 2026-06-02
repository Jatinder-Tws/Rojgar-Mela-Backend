# JobSeeker Roadmap Feature - Backend Implementation Guide

## Overview
This guide provides a comprehensive backend implementation plan for the AI-powered career roadmap feature in your JobSeeker application. The implementation follows your existing FastAPI + SQLAlchemy architecture patterns.

## Architecture Overview

### Current Stack Analysis
- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT-based with role-based access (seeker/provider)
- **AI Integration**: Existing AI services for job creation
- **Structure**: Models → Schemas → Services → Routers → Main

### New Components Required
1. **Models**: Roadmap, Milestone, Resource
2. **Schemas**: Pydantic models for API validation
3. **Services**: Business logic and AI integration
4. **Router**: API endpoints
5. **AI Service**: Roadmap generation with prompts

## 1. Database Models

### Create `models/roadmap.py`

```python
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
    estimated_duration = Column(String(50), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    
    # AI generation metadata
    ai_prompt_version = Column(String(20), default="1.0", nullable=False)
    generation_preferences = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="roadmaps")
    milestones = relationship("Milestone", back_populates="roadmap", cascade="all, delete-orphan")


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    roadmap_id = Column(UUID(as_uuid=False), ForeignKey("roadmaps.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    order_num = Column(Integer, nullable=False)
    skills = Column(ARRAY(String), nullable=True)
    estimated_time = Column(String(50), nullable=True)
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
```

### Update `models/__init__.py`

Add the new imports:
```python
from models.roadmap import Roadmap, Milestone, Resource, MilestoneStatus, ResourceType, DifficultyLevel

__all__ = [
    # ... existing imports ...
    "Roadmap", "Milestone", "Resource", 
    "MilestoneStatus", "ResourceType", "DifficultyLevel",
]
```

### Update `models/user.py`

Add the relationship to User model:
```python
# Add to User class (after existing relationships)
roadmaps = relationship(
    "Roadmap", back_populates="user", cascade="all, delete-orphan"
)
```

## 2. Pydantic Schemas

### Create `schemas/roadmap.py`

```python
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
    order_num: int
    skills: Optional[List[str]] = None
    estimated_time: Optional[str] = None
    status: MilestoneStatus = MilestoneStatus.pending
    dependencies: Optional[List[str]] = None


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


class RoadmapBase(BaseModel):
    target_role: str
    current_level: str
    target_level: str
    skills_to_develop: Optional[List[str]] = None
    estimated_duration: Optional[str] = None


class RoadmapCreate(RoadmapBase):
    milestones: Optional[List[MilestoneCreate]] = None


class RoadmapUpdate(BaseModel):
    target_role: Optional[str] = None
    current_level: Optional[str] = None
    target_level: Optional[str] = None
    skills_to_develop: Optional[List[str]] = None
    estimated_duration: Optional[str] = None
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
```

## 3. AI Service Integration

### Create `services/ai_roadmap_service.py`

```python
import json
import logging
from typing import Dict, List, Optional
from models.user import User
from models.roadmap import Roadmap, Milestone, Resource, ResourceType, DifficultyLevel

logger = logging.getLogger(__name__)


class AIRoadmapService:
    def __init__(self):
        self.prompt_version = "1.0"
    
    async def generate_roadmap(
        self,
        user: User,
        target_role: str,
        current_level: Optional[str] = None,
        target_level: Optional[str] = None,
        learning_preferences: Optional[Dict] = None,
        time_commitment: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate AI-powered roadmap based on user profile and preferences
        """
        
        # Extract user skills and experience
        user_skills = getattr(user, 'skills', [])
        user_experience = getattr(user, 'experience', '0')
        user_industry = getattr(user, 'industry', '')
        
        # Build the AI prompt
        prompt = self._build_roadmap_prompt(
            current_skills=user_skills,
            experience_level=user_experience,
            target_role=target_role,
            current_level=current_level or self._infer_current_level(user_experience),
            target_level=target_level or "senior",
            industry=user_industry,
            learning_preferences=learning_preferences,
            time_commitment=time_commitment,
            focus_areas=focus_areas
        )
        
        try:
            # Call AI service (adapt to your existing AI integration)
            ai_response = await self._call_ai_service(prompt)
            
            # Parse and validate AI response
            roadmap_data = self._parse_ai_response(ai_response)
            
            # Enhance with default resources if needed
            roadmap_data = self._enhance_with_resources(roadmap_data, target_role)
            
            return roadmap_data
            
        except Exception as e:
            logger.error(f"Error generating roadmap: {e}")
            # Return fallback roadmap
            return self._generate_fallback_roadmap(target_role, user_skills)
    
    def _build_roadmap_prompt(
        self,
        current_skills: List[str],
        experience_level: str,
        target_role: str,
        current_level: str,
        target_level: str,
        industry: str,
        learning_preferences: Optional[Dict],
        time_commitment: Optional[str],
        focus_areas: Optional[List[str]]
    ) -> str:
        """
        Build the AI prompt for roadmap generation
        """
        
        prompt = f"""
You are an expert career counselor and technical trainer. Create a personalized learning roadmap for a job seeker.

USER PROFILE:
- Current Skills: {', '.join(current_skills) if current_skills else 'None specified'}
- Experience Level: {experience_level} years
- Industry: {industry}
- Target Role: {target_role}
- Current Level: {current_level}
- Target Level: {target_level}
- Time Commitment: {time_commitment or 'Not specified'}
- Focus Areas: {', '.join(focus_areas) if focus_areas else 'None specified'}

LEARNING PREFERENCES:
{json.dumps(learning_preferences or {}, indent=2)}

Generate a structured learning roadmap with the following requirements:

1. Create 6-8 key milestones in logical progression order
2. Each milestone should include:
   - Clear, actionable title
   - Detailed description of what will be learned
   - Specific skills to develop
   - Estimated time to complete
   - 3-5 recommended resources (mix of free/paid)
   - Dependencies on previous milestones (if any)

3. Resources should include:
   - Online courses (Coursera, Udemy, edX)
   - Documentation and tutorials
   - Practice projects
   - Certifications (if relevant)
   - Video content

4. Consider the user's current skills and experience
5. Focus on practical, job-ready skills
6. Include both technical and soft skills where relevant

FORMAT YOUR RESPONSE AS VALID JSON:
{{
    "roadmap": {{
        "estimated_duration": "X months",
        "skills_to_develop": ["skill1", "skill2", ...],
        "milestones": [
            {{
                "title": "Milestone Title",
                "description": "Detailed description...",
                "order_num": 1,
                "skills": ["skill1", "skill2"],
                "estimated_time": "2-3 weeks",
                "dependencies": [],
                "resources": [
                    {{
                        "title": "Resource Title",
                        "type": "course|article|video|project|certification",
                        "url": "https://example.com",
                        "platform": "Platform Name",
                        "duration": "X hours",
                        "difficulty": "beginner|intermediate|advanced",
                        "description": "Resource description",
                        "is_free": true,
                        "rating": 4.5
                    }}
                ]
            }}
        ]
    }}
}}
"""
        return prompt
    
    async def _call_ai_service(self, prompt: str) -> str:
        """
        Call your existing AI service
        Adapt this to your existing AI integration pattern
        """
        # Example: Using your existing AI service pattern
        # You might need to import your existing AI service
        try:
            # This is where you'd integrate with your existing AI service
            # For now, I'll provide a mock implementation
            
            # If you have an existing AI service, you might call it like:
            # from services.ai_service import generate_content
            # response = await generate_content(prompt)
            # return response
            
            # Mock response for development
            return self._get_mock_ai_response()
            
        except Exception as e:
            logger.error(f"AI service call failed: {e}")
            raise
    
    def _parse_ai_response(self, ai_response: str) -> Dict:
        """
        Parse and validate AI response
        """
        try:
            # Extract JSON from response
            if "```json" in ai_response:
                json_start = ai_response.find("```json") + 7
                json_end = ai_response.find("```", json_start)
                json_str = ai_response[json_start:json_end].strip()
            else:
                json_str = ai_response.strip()
            
            roadmap_data = json.loads(json_str)
            
            # Validate structure
            if "roadmap" not in roadmap_data:
                raise ValueError("Invalid AI response structure")
            
            return roadmap_data["roadmap"]
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response JSON: {e}")
            raise ValueError("Invalid JSON response from AI")
    
    def _enhance_with_resources(self, roadmap_data: Dict, target_role: str) -> Dict:
        """
        Enhance roadmap with additional resources if AI response is limited
        """
        # Add default resources for common skills if needed
        for milestone in roadmap_data.get("milestones", []):
            if len(milestone.get("resources", [])) < 3:
                milestone["resources"] = self._get_default_resources(
                    milestone.get("skills", []), 
                    target_role
                )
        
        return roadmap_data
    
    def _get_default_resources(self, skills: List[str], target_role: str) -> List[Dict]:
        """
        Get default resources for common skills
        """
        default_resources = []
        
        # Common resources for different skill categories
        skill_resources = {
            "python": [
                {
                    "title": "Python for Everybody",
                    "type": "course",
                    "url": "https://www.coursera.org/learn/python",
                    "platform": "Coursera",
                    "duration": "20 hours",
                    "difficulty": "beginner",
                    "description": "Comprehensive Python course for beginners",
                    "is_free": True,
                    "rating": 4.8
                }
            ],
            "javascript": [
                {
                    "title": "JavaScript.info",
                    "type": "article",
                    "url": "https://javascript.info",
                    "platform": "JavaScript.info",
                    "duration": "30 hours",
                    "difficulty": "beginner",
                    "description": "Modern JavaScript tutorial",
                    "is_free": True,
                    "rating": 4.7
                }
            ],
            "react": [
                {
                    "title": "React Tutorial",
                    "type": "video",
                    "url": "https://react.dev/learn",
                    "platform": "React.dev",
                    "duration": "15 hours",
                    "difficulty": "intermediate",
                    "description": "Official React tutorial",
                    "is_free": True,
                    "rating": 4.9
                }
            ]
        }
        
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower in skill_resources:
                default_resources.extend(skill_resources[skill_lower])
        
        return default_resources[:5]  # Limit to 5 resources
    
    def _infer_current_level(self, experience: str) -> str:
        """
        Infer current level from experience
        """
        try:
            exp_years = float(experience)
            if exp_years < 1:
                return "beginner"
            elif exp_years < 3:
                return "junior"
            elif exp_years < 5:
                return "mid-level"
            else:
                return "senior"
        except (ValueError, TypeError):
            return "beginner"
    
    def _generate_fallback_roadmap(self, target_role: str, user_skills: List[str]) -> Dict:
        """
        Generate a basic fallback roadmap if AI fails
        """
        return {
            "estimated_duration": "3-6 months",
            "skills_to_develop": ["Technical Skills", "Soft Skills", "Portfolio Development"],
            "milestones": [
                {
                    "title": "Foundation Skills",
                    "description": f"Build fundamental skills for {target_role}",
                    "order_num": 1,
                    "skills": ["Technical Fundamentals"],
                    "estimated_time": "4-6 weeks",
                    "dependencies": [],
                    "resources": [
                        {
                            "title": "Online Learning Platform",
                            "type": "course",
                            "url": "https://coursera.org",
                            "platform": "Coursera",
                            "duration": "20 hours",
                            "difficulty": "beginner",
                            "description": "Start with fundamental courses",
                            "is_free": True,
                            "rating": 4.5
                        }
                    ]
                },
                {
                    "title": "Practical Experience",
                    "description": "Gain hands-on experience through projects",
                    "order_num": 2,
                    "skills": ["Project Development"],
                    "estimated_time": "6-8 weeks",
                    "dependencies": [],
                    "resources": [
                        {
                            "title": "Project-Based Learning",
                            "type": "project",
                            "url": "https://github.com",
                            "platform": "GitHub",
                            "duration": "40 hours",
                            "difficulty": "intermediate",
                            "description": "Build portfolio projects",
                            "is_free": True,
                            "rating": 4.7
                        }
                    ]
                }
            ]
        }
    
    def _get_mock_ai_response(self) -> str:
        """
        Mock AI response for development/testing
        """
        return """
```json
{
    "roadmap": {
        "estimated_duration": "4-6 months",
        "skills_to_develop": ["Frontend Development", "Backend Development", "Database Management", " Deployment"],
        "milestones": [
            {
                "title": "Frontend Fundamentals",
                "description": "Master HTML, CSS, and JavaScript basics",
                "order_num": 1,
                "skills": ["HTML", "CSS", "JavaScript"],
                "estimated_time": "4-6 weeks",
                "dependencies": [],
                "resources": [
                    {
                        "title": "MDN Web Docs",
                        "type": "article",
                        "url": "https://developer.mozilla.org",
                        "platform": "MDN",
                        "duration": "30 hours",
                        "difficulty": "beginner",
                        "description": "Comprehensive web development documentation",
                        "is_free": true,
                        "rating": 4.8
                    },
                    {
                        "title": "JavaScript: The Good Parts",
                        "type": "book",
                        "url": "https://oreilly.com",
                        "platform": "O'Reilly",
                        "duration": "15 hours",
                        "difficulty": "intermediate",
                        "description": "Essential JavaScript concepts",
                        "is_free": false,
                        "rating": 4.5
                    }
                ]
            },
            {
                "title": "React Development",
                "description": "Learn React and modern frontend frameworks",
                "order_num": 2,
                "skills": ["React", "State Management", "Component Architecture"],
                "estimated_time": "6-8 weeks",
                "dependencies": ["1"],
                "resources": [
                    {
                        "title": "React Official Tutorial",
                        "type": "course",
                        "url": "https://react.dev/learn",
                        "platform": "React.dev",
                        "duration": "20 hours",
                        "difficulty": "intermediate",
                        "description": "Official React learning path",
                        "is_free": true,
                        "rating": 4.9
                    }
                ]
            }
        ]
    }
}
```
        """


# Global instance
ai_roadmap_service = AIRoadmapService()
```

## 4. Business Logic Service

### Create `services/roadmap_service.py`

```python
import logging
from typing import List, Optional, Dict
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.roadmap import Roadmap, Milestone, Resource, MilestoneStatus
from models.user import User
from schemas.roadmap import (
    RoadmapCreate, RoadmapUpdate, RoadmapOut, RoadmapSummary,
    MilestoneCreate, MilestoneUpdate, MilestoneOut, ResourceCreate, ResourceUpdate,
    RoadmapGenerateRequest, MilestoneStatusUpdate, RoadmapProgress
)
from services.ai_roadmap_service import ai_roadmap_service

logger = logging.getLogger(__name__)


class RoadmapService:
    def __init__(self):
        self.ai_service = ai_roadmap_service
    
    async def generate_roadmap(
        self,
        user: User,
        request: RoadmapGenerateRequest,
        db: AsyncSession
    ) -> RoadmapOut:
        """
        Generate a new AI-powered roadmap for the user
        """
        try:
            # Generate roadmap data using AI
            roadmap_data = await self.ai_service.generate_roadmap(
                user=user,
                target_role=request.target_role,
                current_level=request.current_level,
                target_level=request.target_level,
                learning_preferences=request.learning_preferences,
                time_commitment=request.time_commitment,
                focus_areas=request.focus_areas
            )
            
            # Create roadmap record
            roadmap = Roadmap(
                user_id=user.id,
                target_role=request.target_role,
                current_level=request.current_level or "beginner",
                target_level=request.target_level or "senior",
                skills_to_develop=roadmap_data.get("skills_to_develop", []),
                estimated_duration=roadmap_data.get("estimated_duration"),
                ai_prompt_version=self.ai_service.prompt_version,
                generation_preferences={
                    "learning_preferences": request.learning_preferences,
                    "time_commitment": request.time_commitment,
                    "focus_areas": request.focus_areas
                }
            )
            
            db.add(roadmap)
            await db.flush()  # Get the roadmap ID
            
            # Create milestones
            milestones_data = roadmap_data.get("milestones", [])
            for milestone_data in milestones_data:
                milestone = Milestone(
                    roadmap_id=roadmap.id,
                    title=milestone_data["title"],
                    description=milestone_data.get("description"),
                    order_num=milestone_data["order_num"],
                    skills=milestone_data.get("skills", []),
                    estimated_time=milestone_data.get("estimated_time"),
                    dependencies=milestone_data.get("dependencies", [])
                )
                db.add(milestone)
                await db.flush()  # Get the milestone ID
                
                # Create resources
                resources_data = milestone_data.get("resources", [])
                for resource_data in resources_data:
                    resource = Resource(
                        milestone_id=milestone.id,
                        title=resource_data["title"],
                        type=resource_data["type"],
                        url=resource_data.get("url"),
                        platform=resource_data.get("platform"),
                        duration=resource_data.get("duration"),
                        difficulty=resource_data.get("difficulty"),
                        description=resource_data.get("description"),
                        is_free=resource_data.get("is_free", True),
                        rating=resource_data.get("rating")
                    )
                    db.add(resource)
            
            await db.commit()
            await db.refresh(roadmap)
            
            # Load with relationships for response
            return await self.get_roadmap_by_id(roadmap.id, user.id, db)
            
        except Exception as e:
            logger.error(f"Error generating roadmap: {e}")
            await db.rollback()
            raise
    
    async def get_user_roadmaps(
        self, 
        user_id: str, 
        db: AsyncSession,
        limit: int = 10,
        offset: int = 0
    ) -> List[RoadmapSummary]:
        """
        Get all roadmaps for a user with summary information
        """
        try:
            # Query roadmaps with milestone counts
            query = select(
                Roadmap,
                func.count(Milestone.id).label('total_milestones'),
                func.sum(func.case((Milestone.status == MilestoneStatus.completed, 1), else_=0)).label('completed_milestones')
            ).outerjoin(Milestone).where(
                Roadmap.user_id == user_id
            ).group_by(Roadmap.id).order_by(Roadmap.created_at.desc()).offset(offset).limit(limit)
            
            result = await db.execute(query)
            roadmap_data = result.all()
            
            roadmaps = []
            for roadmap, total_milestones, completed_milestones in roadmap_data:
                completed_count = completed_milestones or 0
                total_count = total_milestones or 0
                progress_percentage = (completed_count / total_count * 100) if total_count > 0 else 0
                
                roadmap_summary = RoadmapSummary(
                    id=str(roadmap.id),
                    target_role=roadmap.target_role,
                    current_level=roadmap.current_level,
                    target_level=roadmap.target_level,
                    estimated_duration=roadmap.estimated_duration,
                    status=roadmap.status,
                    progress_percentage=round(progress_percentage, 2),
                    total_milestones=total_count,
                    completed_milestones=completed_count,
                    created_at=roadmap.created_at
                )
                roadmaps.append(roadmap_summary)
            
            return roadmaps
            
        except Exception as e:
            logger.error(f"Error getting user roadmaps: {e}")
            raise
    
    async def get_roadmap_by_id(
        self, 
        roadmap_id: str, 
        user_id: str, 
        db: AsyncSession
    ) -> RoadmapOut:
        """
        Get a specific roadmap with all milestones and resources
        """
        try:
            # Query roadmap with relationships
            result = await db.execute(
                select(Roadmap)
                .options(
                    selectinload(Roadmap.milestones)
                    .selectinload(Milestone.resources)
                )
                .where(Roadmap.id == roadmap_id, Roadmap.user_id == user_id)
            )
            
            roadmap = result.scalar_one_or_none()
            if not roadmap:
                raise ValueError("Roadmap not found")
            
            # Calculate progress
            total_milestones = len(roadmap.milestones)
            completed_milestones = sum(1 for m in roadmap.milestones if m.status == MilestoneStatus.completed)
            progress_percentage = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
            
            # Convert to response model
            roadmap_out = RoadmapOut.model_validate(roadmap)
            roadmap_out.progress_percentage = round(progress_percentage, 2)
            
            return roadmap_out
            
        except Exception as e:
            logger.error(f"Error getting roadmap: {e}")
            raise
    
    async def update_roadmap(
        self,
        roadmap_id: str,
        user_id: str,
        update_data: RoadmapUpdate,
        db: AsyncSession
    ) -> RoadmapOut:
        """
        Update roadmap details
        """
        try:
            # Get roadmap
            result = await db.execute(
                select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.user_id == user_id)
            )
            roadmap = result.scalar_one_or_none()
            if not roadmap:
                raise ValueError("Roadmap not found")
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(roadmap, field, value)
            
            await db.commit()
            await db.refresh(roadmap)
            
            return await self.get_roadmap_by_id(roadmap_id, user_id, db)
            
        except Exception as e:
            logger.error(f"Error updating roadmap: {e}")
            await db.rollback()
            raise
    
    async def delete_roadmap(
        self,
        roadmap_id: str,
        user_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Delete a roadmap
        """
        try:
            # Get roadmap
            result = await db.execute(
                select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.user_id == user_id)
            )
            roadmap = result.scalar_one_or_none()
            if not roadmap:
                raise ValueError("Roadmap not found")
            
            # Delete roadmap (cascade will delete milestones and resources)
            await db.delete(roadmap)
            await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting roadmap: {e}")
            await db.rollback()
            raise
    
    async def update_milestone_status(
        self,
        roadmap_id: str,
        milestone_id: str,
        user_id: str,
        status_update: MilestoneStatusUpdate,
        db: AsyncSession
    ) -> MilestoneOut:
        """
        Update milestone status
        """
        try:
            # Get milestone with roadmap verification
            result = await db.execute(
                select(Milestone)
                .join(Roadmap)
                .options(selectinload(Milestone.resources))
                .where(
                    Milestone.id == milestone_id,
                    Milestone.roadmap_id == roadmap_id,
                    Roadmap.user_id == user_id
                )
            )
            milestone = result.scalar_one_or_none()
            if not milestone:
                raise ValueError("Milestone not found")
            
            # Update status and timestamps
            old_status = milestone.status
            milestone.status = status_update.status
            
            if status_update.status == MilestoneStatus.in_progress and old_status != MilestoneStatus.in_progress:
                milestone.started_at = func.now()
            elif status_update.status == MilestoneStatus.completed and old_status != MilestoneStatus.completed:
                milestone.completed_at = func.now()
            
            await db.commit()
            await db.refresh(milestone)
            
            return MilestoneOut.model_validate(milestone)
            
        except Exception as e:
            logger.error(f"Error updating milestone status: {e}")
            await db.rollback()
            raise
    
    async def get_roadmap_progress(
        self,
        roadmap_id: str,
        user_id: str,
        db: AsyncSession
    ) -> RoadmapProgress:
        """
        Get detailed progress information for a roadmap
        """
        try:
            # Get milestones with counts
            result = await db.execute(
                select(
                    func.count(Milestone.id).label('total'),
                    func.sum(func.case((Milestone.status == MilestoneStatus.completed, 1), else_=0)).label('completed'),
                    func.sum(func.case((Milestone.status == MilestoneStatus.in_progress, 1), else_=0)).label('in_progress'),
                    func.sum(func.case((Milestone.status == MilestoneStatus.pending, 1), else_=0)).label('pending')
                )
                .join(Roadmap)
                .where(Roadmap.id == roadmap_id, Roadmap.user_id == user_id)
            )
            
            counts = result.first()
            total = counts.total or 0
            completed = counts.completed or 0
            in_progress = counts.in_progress or 0
            pending = counts.pending or 0
            
            progress_percentage = (completed / total * 100) if total > 0 else 0
            
            return RoadmapProgress(
                roadmap_id=roadmap_id,
                total_milestones=total,
                completed_milestones=completed,
                in_progress_milestones=in_progress,
                pending_milestones=pending,
                progress_percentage=round(progress_percentage, 2)
            )
            
        except Exception as e:
            logger.error(f"Error getting roadmap progress: {e}")
            raise
    
    async def regenerate_roadmap(
        self,
        roadmap_id: str,
        user_id: str,
        preferences: Dict,
        db: AsyncSession
    ) -> RoadmapOut:
        """
        Regenerate roadmap with new preferences
        """
        try:
            # Get existing roadmap
            result = await db.execute(
                select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.user_id == user_id)
            )
            roadmap = result.scalar_one_or_none()
            if not roadmap:
                raise ValueError("Roadmap not found")
            
            # Delete existing milestones and resources
            await db.execute(
                delete(Milestone).where(Milestone.roadmap_id == roadmap_id)
            )
            
            # Generate new roadmap data
            roadmap_data = await self.ai_service.generate_roadmap(
                user=user,  # You'll need to pass the user object
                target_role=roadmap.target_role,
                current_level=roadmap.current_level,
                target_level=roadmap.target_level,
                learning_preferences=preferences.get("learning_preferences"),
                time_commitment=preferences.get("time_commitment"),
                focus_areas=preferences.get("focus_areas")
            )
            
            # Update roadmap
            roadmap.skills_to_develop = roadmap_data.get("skills_to_develop", [])
            roadmap.estimated_duration = roadmap_data.get("estimated_duration")
            roadmap.generation_preferences = preferences
            
            # Create new milestones
            milestones_data = roadmap_data.get("milestones", [])
            for milestone_data in milestones_data:
                milestone = Milestone(
                    roadmap_id=roadmap.id,
                    title=milestone_data["title"],
                    description=milestone_data.get("description"),
                    order_num=milestone_data["order_num"],
                    skills=milestone_data.get("skills", []),
                    estimated_time=milestone_data.get("estimated_time"),
                    dependencies=milestone_data.get("dependencies", [])
                )
                db.add(milestone)
                await db.flush()
                
                # Create resources
                resources_data = milestone_data.get("resources", [])
                for resource_data in resources_data:
                    resource = Resource(
                        milestone_id=milestone.id,
                        title=resource_data["title"],
                        type=resource_data["type"],
                        url=resource_data.get("url"),
                        platform=resource_data.get("platform"),
                        duration=resource_data.get("duration"),
                        difficulty=resource_data.get("difficulty"),
                        description=resource_data.get("description"),
                        is_free=resource_data.get("is_free", True),
                        rating=resource_data.get("rating")
                    )
                    db.add(resource)
            
            await db.commit()
            await db.refresh(roadmap)
            
            return await self.get_roadmap_by_id(roadmap_id, user_id, db)
            
        except Exception as e:
            logger.error(f"Error regenerating roadmap: {e}")
            await db.rollback()
            raise


# Global service instance
roadmap_service = RoadmapService()
```

## 5. API Router

### Create `routers/roadmap.py`

```python
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.roadmap import MilestoneStatus
from schemas.roadmap import (
    RoadmapOut, RoadmapSummary, RoadmapGenerateRequest,
    MilestoneOut, MilestoneStatusUpdate, RoadmapProgress, RoadmapUpdate
)
from services.auth_service import require_seeker, require_verified
from services.roadmap_service import roadmap_service

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


@router.post("/generate", response_model=RoadmapOut, status_code=201)
async def generate_roadmap(
    request: RoadmapGenerateRequest,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new AI-powered roadmap
    """
    try:
        return await roadmap_service.generate_roadmap(user, request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate roadmap")


@router.get("", response_model=List[RoadmapSummary])
async def get_user_roadmaps(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all roadmaps for the authenticated user
    """
    try:
        return await roadmap_service.get_user_roadmaps(user.id, db, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch roadmaps")


@router.get("/{roadmap_id}", response_model=RoadmapOut)
async def get_roadmap(
    roadmap_id: str,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific roadmap with all milestones and resources
    """
    try:
        return await roadmap_service.get_roadmap_by_id(roadmap_id, user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch roadmap")


@router.patch("/{roadmap_id}", response_model=RoadmapOut)
async def update_roadmap(
    roadmap_id: str,
    update_data: RoadmapUpdate,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    """
    Update roadmap details
    """
    try:
        return await roadmap_service.update_roadmap(roadmap_id, user.id, update_data, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update roadmap")


@router.delete("/{roadmap_id}", status_code=204)
async def delete_roadmap(
    roadmap_id: str,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a roadmap
    """
    try:
        await roadmap_service.delete_roadmap(roadmap_id, user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete roadmap")


@router.put("/{roadmap_id}/milestones/{milestone_id}/status", response_model=MilestoneOut)
async def update_milestone_status(
    roadmap_id: str,
    milestone_id: str,
    status_update: MilestoneStatusUpdate,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    """
    Update milestone status
    """
    try:
        return await roadmap_service.update_milestone_status(
            roadmap_id, milestone_id, user.id, status_update, db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update milestone status")


@router.get("/{roadmap_id}/progress", response_model=RoadmapProgress)
async def get_roadmap_progress(
    roadmap_id: str,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed progress information for a roadmap
    """
    try:
        return await roadmap_service.get_roadmap_progress(roadmap_id, user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch roadmap progress")


@router.post("/{roadmap_id}/regenerate", response_model=RoadmapOut)
async def regenerate_roadmap(
    roadmap_id: str,
    preferences: dict,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate roadmap with new preferences
    """
    try:
        return await roadmap_service.regenerate_roadmap(roadmap_id, user.id, preferences, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to regenerate roadmap")


@router.get("/{roadmap_id}/milestones/{milestone_id}", response_model=MilestoneOut)
async def get_milestone(
    roadmap_id: str,
    milestone_id: str,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific milestone with resources
    """
    try:
        # Get the full roadmap and find the specific milestone
        roadmap = await roadmap_service.get_roadmap_by_id(roadmap_id, user.id, db)
        
        for milestone in roadmap.milestones:
            if milestone.id == milestone_id:
                return milestone
        
        raise ValueError("Milestone not found")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch milestone")
```

## 6. Database Migration

### Create migration script `migrations/add_roadmap_tables.py`

```python
"""
Migration script to add roadmap tables
Run this script to create the new tables in your database
"""

async def add_roadmap_tables():
    """Add roadmap, milestone, and resource tables"""
    
    # SQL statements to create tables
    create_roadmaps_table = """
    CREATE TABLE IF NOT EXISTS roadmaps (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        target_role VARCHAR(100) NOT NULL,
        current_level VARCHAR(50) NOT NULL,
        target_level VARCHAR(50) NOT NULL,
        skills_to_develop TEXT[],
        estimated_duration VARCHAR(50),
        status VARCHAR(20) DEFAULT 'active' NOT NULL,
        ai_prompt_version VARCHAR(20) DEFAULT '1.0' NOT NULL,
        generation_preferences JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_roadmaps_user_id ON roadmaps(user_id);
    CREATE INDEX IF NOT EXISTS idx_roadmaps_created_at ON roadmaps(created_at DESC);
    """
    
    create_milestones_table = """
    CREATE TABLE IF NOT EXISTS milestones (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        order_num INTEGER NOT NULL,
        skills TEXT[],
        estimated_time VARCHAR(50),
        status VARCHAR(20) DEFAULT 'pending' NOT NULL,
        dependencies UUID[],
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_milestones_roadmap_id ON milestones(roadmap_id);
    CREATE INDEX IF NOT EXISTS idx_milestones_status ON milestones(status);
    CREATE INDEX IF NOT EXISTS idx_milestones_order ON milestones(roadmap_id, order_num);
    """
    
    create_resources_table = """
    CREATE TABLE IF NOT EXISTS resources (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        milestone_id UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
        title VARCHAR(200) NOT NULL,
        type VARCHAR(20) NOT NULL,
        url TEXT,
        platform VARCHAR(100),
        duration VARCHAR(50),
        difficulty VARCHAR(20),
        description TEXT,
        is_free BOOLEAN DEFAULT true NOT NULL,
        rating FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_resources_milestone_id ON resources(milestone_id);
    CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type);
    CREATE INDEX IF NOT EXISTS idx_resources_difficulty ON resources(difficulty);
    """
    
    # Create triggers for updated_at
    create_triggers = """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    
    DROP TRIGGER IF EXISTS update_roadmaps_updated_at ON roadmaps;
    CREATE TRIGGER update_roadmaps_updated_at 
        BEFORE UPDATE ON roadmaps 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    DROP TRIGGER IF EXISTS update_milestones_updated_at ON milestones;
    CREATE TRIGGER update_milestones_updated_at 
        BEFORE UPDATE ON milestones 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    DROP TRIGGER IF EXISTS update_resources_updated_at ON resources;
    CREATE TRIGGER update_resources_updated_at 
        BEFORE UPDATE ON resources 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    
    return [create_roadmaps_table, create_milestones_table, create_resources_table, create_triggers]


# Usage in your init_db function
async def init_roadmap_tables(conn):
    """Initialize roadmap tables"""
    migration_statements = await add_roadmap_tables()
    
    for statement in migration_statements:
        await conn.execute(__import__("sqlalchemy").text(statement))
```

## 7. Update Main Application

### Update `main.py`

Add the roadmap router import:

```python
# Add to the imports section
from routers import auth, users, jobs, resumes, matches, applications, notifications, interviews, assessment, portfolio, analytics, resume_builder, onboarding, master, ai_interview, roadmap  # noqa

# Add to the router registrations
app.include_router(roadmap.router, prefix="/api")
```

### Update `database.py`

Add the roadmap model import to the init_db function:

```python
# Update the import line in init_db function
from models import user, resume, job, match, application, notification, otp, interview, assessment, portfolio, master, ai_interview, roadmap  # noqa
```

## 8. Testing

### Create `tests/test_roadmap.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User, UserRole
from schemas.roadmap import RoadmapGenerateRequest


@pytest.mark.asyncio
async def test_generate_roadmap(client: TestClient, db: AsyncSession, seeker_user: User):
    """Test roadmap generation"""
    request_data = {
        "target_role": "Full Stack Developer",
        "current_level": "beginner",
        "target_level": "senior",
        "learning_preferences": {"visual_learning": True},
        "time_commitment": "10 hours/week",
        "focus_areas": ["React", "Node.js"]
    }
    
    response = client.post(
        "/api/roadmaps/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {seeker_user.access_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["target_role"] == "Full Stack Developer"
    assert len(data["milestones"]) > 0
    assert "progress_percentage" in data


@pytest.mark.asyncio
async def test_get_user_roadmaps(client: TestClient, db: AsyncSession, seeker_user: User):
    """Test getting user roadmaps"""
    response = client.get(
        "/api/roadmaps",
        headers={"Authorization": f"Bearer {seeker_user.access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_update_milestone_status(client: TestClient, db: AsyncSession, seeker_user: User):
    """Test updating milestone status"""
    # First create a roadmap
    request_data = {
        "target_role": "Frontend Developer",
        "current_level": "beginner"
    }
    
    create_response = client.post(
        "/api/roadmaps/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {seeker_user.access_token}"}
    )
    
    roadmap = create_response.json()
    milestone_id = roadmap["milestones"][0]["id"]
    
    # Update milestone status
    update_data = {"status": "in_progress"}
    response = client.put(
        f"/api/roadmaps/{roadmap['id']}/milestones/{milestone_id}/status",
        json=update_data,
        headers={"Authorization": f"Bearer {seeker_user.access_token}"}
    )
    
    assert response.status_code == 200
    updated_milestone = response.json()
    assert updated_milestone["status"] == "in_progress"
```

## 9. Environment Variables

### Update `.env.example`

```env
# Add these to your existing environment variables

# AI Roadmap Service Configuration
AI_ROADMAP_MODEL=gpt-4
AI_ROADMAP_TEMPERATURE=0.7
AI_ROADMAP_MAX_TOKENS=4000

# Roadmap Feature Flags
ENABLE_ROADMAP_FEATURE=true
ROADMAP_MAX_PER_USER=5
ROADMAP_CACHE_TTL=3600
```

## 10. API Documentation

The following endpoints will be available:

### Roadmap Management
- `POST /api/roadmaps/generate` - Generate new AI-powered roadmap
- `GET /api/roadmaps` - Get user's roadmaps (paginated)
- `GET /api/roadmaps/{id}` - Get specific roadmap
- `PATCH /api/roadmaps/{id}` - Update roadmap details
- `DELETE /api/roadmaps/{id}` - Delete roadmap
- `POST /api/roadmaps/{id}/regenerate` - Regenerate with new preferences

### Milestone Management
- `PUT /api/roadmaps/{id}/milestones/{milestone_id}/status` - Update milestone status
- `GET /api/roadmaps/{id}/milestones/{milestone_id}` - Get milestone details

### Progress Tracking
- `GET /api/roadmaps/{id}/progress` - Get roadmap progress

## 11. Integration Points

### User Profile Integration
The roadmap service integrates with existing user data:
- User skills from profile
- Experience level
- Industry preferences
- Learning preferences

### AI Service Integration
- Uses your existing AI service infrastructure
- Follows your current AI integration patterns
- Includes fallback mechanisms

### Authentication
- Uses existing `require_seeker` and `require_verified` decorators
- Follows your current authentication patterns

## 12. Performance Considerations

### Database Optimization
- Added proper indexes on frequently queried columns
- Used efficient joins for milestone progress calculations
- Implemented pagination for roadmap listings

### Caching
- Consider caching AI-generated roadmaps
- Cache milestone progress calculations
- Use Redis for session caching if needed

### Background Tasks
- AI roadmap generation can be moved to background tasks
- Progress tracking updates can be async

## 13. Security Considerations

### Input Validation
- All inputs validated through Pydantic schemas
- SQL injection prevention through SQLAlchemy ORM
- XSS prevention through proper escaping

### Authorization
- User can only access their own roadmaps
- Role-based access control (seeker only)
- Proper authentication checks

### Rate Limiting
- Consider rate limiting AI generation endpoints
- Limit number of roadmaps per user

## 14. Monitoring and Logging

### Logging
- Comprehensive error logging
- Performance metrics logging
- User activity tracking

### Metrics to Track
- Roadmap generation success rate
- AI service response times
- User engagement metrics
- Milestone completion rates

## 15. Next Steps

1. **Database Migration**: Run the migration script to create tables
2. **Testing**: Implement comprehensive test suite
3. **Frontend Integration**: Coordinate with frontend team
4. **AI Service Integration**: Connect with your existing AI service
5. **Performance Testing**: Load test the AI generation endpoints
6. **Monitoring**: Set up monitoring and alerting

## 16. Troubleshooting

### Common Issues
1. **AI Service Failures**: Check AI service configuration and API keys
2. **Database Issues**: Verify migrations and indexes
3. **Performance**: Check query performance and add caching
4. **Authentication**: Verify user roles and permissions

### Debugging Tips
- Enable SQL logging to debug database queries
- Add detailed logging for AI service calls
- Use FastAPI's built-in debugging features
- Monitor AI service response times

This implementation guide provides a complete backend solution for your roadmap feature that integrates seamlessly with your existing JobSeeker application architecture.
