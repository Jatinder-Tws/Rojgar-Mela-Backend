from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.auth import UserOut, OnboardingRequest
from services.auth_service import require_verified
from routers.users import complete_onboarding

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

@router.post("/complete", response_model=UserOut)
async def onboarding_complete_alias(
    body: OnboardingRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """Alias for users.complete_onboarding to match frontend API definition."""
    return await complete_onboarding(body, background_tasks, user, db)
