from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.shared.schemas.auth import UserOut, OnboardingRequest, UpdateSettingsRequest, UpdateSettingsResponse
from app.core.dependencies import require_verified, get_current_user
from app.shared.controllers.users_controller import (
    get_me as ctrl_get_me,
    complete_onboarding as ctrl_complete_onboarding,
    update_settings as ctrl_update_settings,
    upload_profile_pic as ctrl_upload_profile_pic,
    get_public_user as ctrl_get_public_user,
    delete_own_account as ctrl_delete_own_account,
)
from fastapi import File, UploadFile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return await ctrl_get_me(user)


@router.patch("/me/onboarding", response_model=UserOut)
async def complete_onboarding(body: OnboardingRequest, background_tasks: BackgroundTasks, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_complete_onboarding(body, background_tasks, user, db)


@router.patch("/me/settings", response_model=UpdateSettingsResponse)
async def update_settings(body: UpdateSettingsRequest, background_tasks: BackgroundTasks, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_settings(body, background_tasks, user, db)


@router.post("/me/profile-pic", response_model=UserOut)
async def upload_profile_pic(file: UploadFile = File(...), user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_upload_profile_pic(file, user, db)


@router.delete("/me", status_code=204)
async def delete_own_account(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    """Permanently delete the authenticated user's own account."""
    await ctrl_delete_own_account(user, db)


@router.get("/public/{user_id}", response_model=UserOut)
async def get_public_user(user_id: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_get_public_user(user_id, db)
