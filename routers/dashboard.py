from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from services.auth_service import require_seeker, require_provider
from controllers.dashboard_controller import (
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
