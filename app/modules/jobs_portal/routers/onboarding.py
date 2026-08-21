from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.shared.schemas.auth import UserOut, OnboardingRequest
from app.core.dependencies import require_verified
from app.shared.controllers.users_controller import complete_onboarding

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
