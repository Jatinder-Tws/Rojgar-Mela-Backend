from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin
from app.modules.jobs_portal.schemas.career_roadmap import (
    CareerRoadmapCreate,
    CareerRoadmapImageUploadResponse,
    CareerRoadmapListResponse,
    CareerRoadmapOut,
    CareerRoadmapUpdate,
)
from app.modules.jobs_portal.services import career_roadmap_service as svc
from app.shared.models.user import User

router = APIRouter(prefix="/super-admin", tags=["super-admin-roadmaps"])


@router.get("/career-roadmaps", response_model=CareerRoadmapListResponse)
async def list_career_roadmaps(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    items, total = await svc.list_roadmaps(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status_filter,
        category=category,
        published_only=False,
    )
    return CareerRoadmapListResponse(
        items=[svc._to_list_item(row) for row in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/career-roadmaps/upload-image", response_model=CareerRoadmapImageUploadResponse)
async def upload_career_roadmap_image(
    file: UploadFile = File(...),
    _admin: User = Depends(require_super_admin),
):
    url = await svc.save_hero_image(file)
    return CareerRoadmapImageUploadResponse(url=url)


@router.post("/career-roadmaps", response_model=CareerRoadmapOut, status_code=status.HTTP_201_CREATED)
async def create_career_roadmap(
    body: CareerRoadmapCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    row = await svc.create_roadmap(db, body, admin.id)
    return svc._to_out(row)


@router.get("/career-roadmaps/{roadmap_id}", response_model=CareerRoadmapOut)
async def get_career_roadmap(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    row = await svc.get_by_id(db, roadmap_id)
    return svc._to_out(row)


@router.put("/career-roadmaps/{roadmap_id}", response_model=CareerRoadmapOut)
async def update_career_roadmap(
    roadmap_id: str,
    body: CareerRoadmapUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    row = await svc.update_roadmap(db, roadmap_id, body)
    return svc._to_out(row)


@router.delete("/career-roadmaps/{roadmap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_career_roadmap(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    await svc.delete_roadmap(db, roadmap_id)
    return None
