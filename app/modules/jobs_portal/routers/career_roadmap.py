from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.jobs_portal.schemas.career_roadmap import CareerRoadmapOut, CareerRoadmapPublicListResponse
from app.modules.jobs_portal.services import career_roadmap_service as svc

router = APIRouter(tags=["career-roadmaps"])


@router.get("/career-roadmaps", response_model=CareerRoadmapPublicListResponse)
async def list_public_career_roadmaps(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await svc.list_roadmaps(
        db,
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        published_only=True,
    )
    return CareerRoadmapPublicListResponse(
        items=[svc._to_out(row) for row in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/career-roadmaps/{slug}", response_model=CareerRoadmapOut)
async def get_public_career_roadmap(slug: str, db: AsyncSession = Depends(get_db)):
    row = await svc.get_by_slug(db, slug, published_only=True)
    return svc._to_out(row)
