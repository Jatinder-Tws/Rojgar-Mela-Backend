from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin_or_permission
from app.modules.jobs_portal.schemas.career_roadmap_option import (
    RoadmapOptionCreate,
    RoadmapOptionListResponse,
    RoadmapOptionOut,
    RoadmapOptionUpdate,
)
from app.modules.jobs_portal.services import career_roadmap_option_service as opt_svc
from app.shared.models.user import User

router = APIRouter(prefix="/super-admin/career-roadmap-options", tags=["super-admin-roadmap-options"])


@router.get("/{kind}", response_model=RoadmapOptionListResponse)
async def list_roadmap_options(
    kind: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin_or_permission("roadmaps")),
):
    items = await opt_svc.list_options(db, kind)
    return RoadmapOptionListResponse(items=items)


@router.post("/{kind}", response_model=RoadmapOptionOut, status_code=status.HTTP_201_CREATED)
async def create_roadmap_option(
    kind: str,
    body: RoadmapOptionCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin_or_permission("roadmaps")),
):
    return await opt_svc.create_option(db, kind, body)


@router.put("/{kind}/{option_id}", response_model=RoadmapOptionOut)
async def update_roadmap_option(
    kind: str,
    option_id: str,
    body: RoadmapOptionUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin_or_permission("roadmaps")),
):
    return await opt_svc.update_option(db, kind, option_id, body)


@router.delete("/{kind}/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roadmap_option(
    kind: str,
    option_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin_or_permission("roadmaps")),
):
    await opt_svc.delete_option(db, kind, option_id)
    return None
