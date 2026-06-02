from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.roadmap import MilestoneStatus
from schemas.roadmap import (
    RoadmapOut, RoadmapSummary, RoadmapGenerateRequest,
    MilestoneOut, MilestoneStatusUpdate, RoadmapProgress, RoadmapUpdate,
    RoadmapCategoryOut, RoadmapRoleOut
)
from services.auth_service import require_seeker, require_verified
from services.roadmap_service import roadmap_service

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


@router.get("/categories", response_model=List[RoadmapCategoryOut])
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all roadmap categories with their roles
    """
    try:
        return await roadmap_service.get_categories(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


@router.get("/categories/{category_id}/roles", response_model=List[RoadmapRoleOut])
async def get_category_roles(
    category_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all roles for a specific category
    """
    try:
        return await roadmap_service.get_category_roles(category_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch roles")


@router.get("/suggested-roles", response_model=List[str])
async def suggest_roles(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    """
    Suggest potential target roles based on user profile
    """
    try:
        return await roadmap_service.suggest_roles(user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to suggest roles")


@router.post("/generate", response_model=RoadmapOut)
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
        print("Getting the roadmap by id")
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
        return await roadmap_service.regenerate_roadmap(roadmap_id, user, preferences, db)
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
