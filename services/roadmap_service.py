import logging
from typing import List, Optional, Dict
from sqlalchemy import select, update, delete, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.roadmap import Roadmap, Milestone, Resource, MilestoneStatus, RoadmapCategory, RoadmapRole
from models.user import User
from models.portfolio import Portfolio  # Ensure Portfolio is registered for backref
from schemas.roadmap import (
    RoadmapCreate, RoadmapUpdate, RoadmapOut, RoadmapSummary,
    MilestoneCreate, MilestoneUpdate, MilestoneOut, ResourceCreate, ResourceUpdate,
    RoadmapGenerateRequest, MilestoneStatusUpdate, RoadmapProgress,
    RoadmapCategoryOut, RoadmapRoleOut
)
from services.ai_roadmap_service import ai_roadmap_service

logger = logging.getLogger(__name__)


class RoadmapService:
    def __init__(self):
        self.ai_service = ai_roadmap_service

    async def _find_existing_roadmap(
        self,
        user_id: str,
        request: RoadmapGenerateRequest,
        db: AsyncSession
    ) -> Optional[Roadmap]:
        """
        Return the latest active roadmap matching the user's target role/levels.
        """
        target_role = request.target_role.strip()
        current_level = (request.current_level or "beginner").strip()
        target_level = (request.target_level or "senior").strip()

        result = await db.execute(
            select(Roadmap)
            .where(
                Roadmap.user_id == user_id,
                Roadmap.target_role == target_role,
                Roadmap.current_level == current_level,
                Roadmap.target_level == target_level,
                Roadmap.status == "active"
            )
            .order_by(Roadmap.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def suggest_roles(self, user: User, db: AsyncSession) -> List[str]:
        """
        Suggest potential career roles for the user
        """
        try:
            logger.info(f"Suggesting roles for user: {user.id}")
            # Load portfolio relationship if not already loaded
            query = select(User).options(selectinload(User.portfolio)).where(User.id == user.id)
            result = await db.execute(query)
            user_with_portfolio = result.scalar_one_or_none()
            
            roles = await self.ai_service.suggest_roles(user_with_portfolio or user)
            logger.info(f"Successfully suggested {len(roles)} roles for user {user.id}")
            return roles
        except Exception as e:
            logger.error(f"Error in RoadmapService.suggest_roles: {e}", exc_info=True)
            raise

    async def get_categories(self, db: AsyncSession) -> List[RoadmapCategoryOut]:
        """
        Get all roadmap categories with their roles
        """
        try:
            result = await db.execute(
                select(RoadmapCategory).options(selectinload(RoadmapCategory.roles))
            )
            categories = result.scalars().all()
            return [RoadmapCategoryOut.model_validate(c) for c in categories]
        except Exception as e:
            logger.error(f"Error getting roadmap categories: {e}")
            raise

    async def get_category_roles(self, category_id: str, db: AsyncSession) -> List[RoadmapRoleOut]:
        """
        Get all roles for a specific category
        """
        try:
            result = await db.execute(
                select(RoadmapRole).where(RoadmapRole.category_id == category_id)
            )
            roles = result.scalars().all()
            return [RoadmapRoleOut.model_validate(r) for r in roles]
        except Exception as e:
            logger.error(f"Error getting category roles: {e}")
            raise

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
            # normalized_current_skills = self._normalize_skills_input(request.current_skills)
            # Load portfolio
            query = select(User).options(selectinload(User.portfolio)).where(User.id == user.id)
            result = await db.execute(query)
            user_with_portfolio = result.scalar_one_or_none()
            user = user_with_portfolio or user


            # Generate roadmap data using AI
            roadmap_data = await self.ai_service.generate_roadmap(
                user=user,
                target_role=request.target_role,
                current_level=request.current_level,
                target_level=request.target_level,
                learning_preferences=request.learning_preferences,
                time_commitment=request.time_commitment,
                focus_areas=request.focus_areas,
                current_skills=request.current_skills
            )
            # print("The road map data is ",roadmap_data)
            print(request.current_skills)
            
            # Upsert by user + target_role + levels: always regenerate content, but reuse same roadmap row if present.
            # existing_roadmap = await self._find_existing_roadmap(user.id, request, db)
            # print("The existing roadmap is",existing_roadmap)
            # if existing_roadmap:
            #     await db.execute(delete(Milestone).where(Milestone.roadmap_id == existing_roadmap.id))
            #     roadmap = existing_roadmap
            #     roadmap.current_level = request.current_level or "beginner"
            #     roadmap.target_level = request.target_level or "senior"
            #     roadmap.skills_to_develop = roadmap_data.get("skills_to_develop", [])
            #     roadmap.current_skills = normalized_current_skills or roadmap_data.get("current_skills", [])
            #     roadmap.estimated_duration = roadmap_data.get("estimated_duration")
            #     roadmap.market_based_salary = roadmap_data.get("market_based_salary")
            #     roadmap.ai_prompt_version = self.ai_service.prompt_version
            #     roadmap.generation_preferences = {
            #         "learning_preferences": request.learning_preferences,
            #         "time_commitment": request.time_commitment,
            #         "focus_areas": request.focus_areas
            #     }
            # else:
            roadmap = Roadmap(
                    user_id=user.id,
                    target_role=request.target_role,
                    current_level=request.current_level or "beginner",
                    target_level=request.target_level or "senior",
                    skills_to_develop=roadmap_data.get("skills_to_develop", []),
                    current_skills= request.current_skills or roadmap_data.get("current_skills", []),
                    estimated_duration=roadmap_data.get("estimated_duration"),
                    market_based_salary=roadmap_data.get("market_based_salary"),
                    ai_prompt_version=self.ai_service.prompt_version,
                    generation_preferences={
                        "learning_preferences": request.learning_preferences,
                        "time_commitment": request.time_commitment,
                        "focus_areas": request.focus_areas
                    }
                )
            db.add(roadmap)

            await db.flush()  # Ensure roadmap ID
            
            # Create milestones
            milestones_data = roadmap_data.get("milestones", [])
            for milestone_data in milestones_data:
                milestone = Milestone(
                    roadmap_id=roadmap.id,
                    title=milestone_data["title"],
                    description=milestone_data.get("description"),
                    stage_title=milestone_data.get("stage_title", "General"),
                    stage_order=milestone_data.get("stage_order", 1),
                    order_num=milestone_data["order_num"],
                    skills=milestone_data.get("skills", []),
                    estimated_time=milestone_data.get("estimated_time"),
                    difficulty=milestone_data.get("difficulty", "intermediate"),
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

    def _normalize_skills_input(self, current_skills) -> List[str]:
        if current_skills is None:
            return []
        if isinstance(current_skills, list):
            cleaned = [str(s).strip() for s in current_skills if str(s).strip()]
            # Handle malformed char-array payloads like ["{","H","T","M","L",...,"}"]
            if cleaned and all(len(x) == 1 for x in cleaned):
                joined = "".join(cleaned).strip().strip("{}[]")
                if joined:
                    return [p.strip().strip("'\"") for p in joined.split(",") if p.strip().strip("'\"")]
            return cleaned
        if isinstance(current_skills, str):
            text = current_skills.strip().strip("{}[]")
            if not text:
                return []
            return [p.strip().strip("'\"") for p in text.split(",") if p.strip().strip("'\"")]
        return []
    
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
                func.sum(case((Milestone.status == MilestoneStatus.completed, 1), else_=0)).label('completed_milestones')
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
                    func.sum(case((Milestone.status == MilestoneStatus.completed, 1), else_=0)).label('completed'),
                    func.sum(case((Milestone.status == MilestoneStatus.in_progress, 1), else_=0)).label('in_progress'),
                    func.sum(case((Milestone.status == MilestoneStatus.pending, 1), else_=0)).label('pending')
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
        user: User,
        preferences: Dict,
        db: AsyncSession
    ) -> RoadmapOut:
        """
        Regenerate roadmap with new preferences
        """
        try:
            # Get existing roadmap
            result = await db.execute(
                select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.user_id == user.id)
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
                user=user,
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
            roadmap.market_based_salary = roadmap_data.get("market_based_salary")
            roadmap.generation_preferences = preferences
            
            # Create new milestones
            milestones_data = roadmap_data.get("milestones", [])
            for milestone_data in milestones_data:
                milestone = Milestone(
                    roadmap_id=roadmap.id,
                    title=milestone_data["title"],
                    description=milestone_data.get("description"),
                    stage_title=milestone_data.get("stage_title", "General"),
                    stage_order=milestone_data.get("stage_order", 1),
                    order_num=milestone_data["order_num"],
                    skills=milestone_data.get("skills", []),
                    estimated_time=milestone_data.get("estimated_time"),
                    difficulty=milestone_data.get("difficulty", "intermediate"),
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
            
            return await self.get_roadmap_by_id(roadmap_id, user.id, db)
            
        except Exception as e:
            logger.error(f"Error regenerating roadmap: {e}")
            await db.rollback()
            raise


# Global service instance
roadmap_service = RoadmapService()
