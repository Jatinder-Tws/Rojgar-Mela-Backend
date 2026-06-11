from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from services.auth_service import require_seeker, require_provider
from controllers.analytics_controller import (
    seeker_stats as ctrl_seeker_stats,
    provider_stats as ctrl_provider_stats,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/seeker")
async def get_seeker_analytics(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_seeker_stats(user, db)


@router.get("/provider")
async def get_provider_analytics(user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_provider_stats(user, db)
