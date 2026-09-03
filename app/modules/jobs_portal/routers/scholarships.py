from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.jobs_portal.controllers.scholarships_controller import ScholarshipsController

router = APIRouter(prefix="/scholarships", tags=["Scholarships"])


@router.get("", summary="Get paginated scholarships with filters and Redis caching")
async def get_scholarships(
    search: Optional[str] = Query(None, description="Search by title, organization, description"),
    source: Optional[str] = Query(None, description="Filter by source platform: 'unstop' or 'buddy4study'"),
    education_level: Optional[str] = Query(None, description="Filter by education level e.g. 'School', 'Undergraduate', 'Postgraduate'"),
    gender: Optional[str] = Query(None, description="Filter by gender eligibility e.g. 'Female', 'All'"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    sort_by: str = Query("deadline_asc", description="Sort order: 'deadline_asc', 'recent', 'featured'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=50, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve public list of active scholarships aggregated from Unstop and Buddy4Study."""
    return await ScholarshipsController.get_scholarships(
        db=db,
        search=search,
        source=source,
        education_level=education_level,
        gender=gender,
        is_featured=is_featured,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", summary="Get scholarship summary metrics and platform counts")
async def get_scholarship_stats(db: AsyncSession = Depends(get_db)):
    """Retrieve summary counts for active opportunities, featured programs, and partner sources."""
    return await ScholarshipsController.get_scholarship_stats(db=db)


@router.get("/{identifier}", summary="Get single scholarship details by ID or slug")
async def get_scholarship_by_id(identifier: str, db: AsyncSession = Depends(get_db)):
    """Retrieve single scholarship opportunity by its UUID or unique slug."""
    return await ScholarshipsController.get_scholarship_by_id_or_slug(db=db, identifier=identifier)


@router.post("/sync", summary="Trigger manual live synchronization from external platforms")
async def trigger_scholarship_sync():
    """Immediately execute the scholarship scraper & sync pipeline and refresh the Redis cache."""
    return await ScholarshipsController.trigger_manual_sync()
