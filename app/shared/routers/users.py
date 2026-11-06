from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.shared.schemas.auth import UserOut, OnboardingRequest, UpdateSettingsRequest, UpdateSettingsResponse
from app.core.dependencies import require_verified, get_current_user, require_authenticated
from app.shared.controllers.users_controller import (
    get_me as ctrl_get_me,
    complete_onboarding as ctrl_complete_onboarding,
    update_settings as ctrl_update_settings,
    phone_is_available as ctrl_phone_is_available,
    upload_profile_pic as ctrl_upload_profile_pic,
    get_public_user as ctrl_get_public_user,
    get_existing_public_user_ids as ctrl_get_existing_public_user_ids,
    delete_own_account as ctrl_delete_own_account,
)

router = APIRouter(prefix="/users", tags=["users"])


class ExistingUserIdsRequest(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=100)


class ExistingUserIdsResponse(BaseModel):
    existing: list[str]


class PhoneAvailabilityResponse(BaseModel):
    available: bool


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_me(user, db)


@router.patch("/me/onboarding", response_model=UserOut)
async def complete_onboarding(body: OnboardingRequest, background_tasks: BackgroundTasks, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_complete_onboarding(body, background_tasks, user, db)


@router.get("/me/phone-availability", response_model=PhoneAvailabilityResponse)
async def phone_availability(
    phone: str = Query(min_length=10, max_length=20),
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """Whether this login number can be saved. Does not reveal who already uses it."""
    return PhoneAvailabilityResponse(available=await ctrl_phone_is_available(phone, user, db))


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


@router.post("/public/existing-ids", response_model=ExistingUserIdsResponse)
async def get_existing_public_user_ids(
    body: ExistingUserIdsRequest,
    _user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Batch-check which public user IDs still exist (deleted accounts are omitted)."""
    existing = await ctrl_get_existing_public_user_ids(body.ids, db)
    return ExistingUserIdsResponse(existing=existing)


@router.get("/public/{user_id}", response_model=UserOut)
async def get_public_user(user_id: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_get_public_user(user_id, db)
