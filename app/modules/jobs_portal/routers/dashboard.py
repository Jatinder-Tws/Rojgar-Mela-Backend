from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.core.dependencies import require_seeker, require_provider
from app.modules.jobs_portal.controllers.dashboard_controller import (
    provider_dashboard as ctrl_provider_dashboard,
    seeker_dashboard as ctrl_seeker_dashboard,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/provider")
async def get_provider_dashboard(
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_provider_dashboard(user, db)


@router.get("/seeker")
async def get_seeker_dashboard(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_seeker_dashboard(user, db)
