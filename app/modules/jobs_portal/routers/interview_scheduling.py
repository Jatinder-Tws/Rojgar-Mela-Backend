from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.modules.jobs_portal.schemas.interview_scheduling import (
    AutoScheduleToggle,
    ProviderInterviewSettingsOut,
    ProviderInterviewSettingsUpdate,
    SlotPreviewListOut,
)
from app.core.dependencies import require_provider
from app.modules.jobs_portal.services.interview_scheduling_service import preview_available_slots
from app.modules.jobs_portal.services.interview_scheduling_dbservice import (
    get_or_create_settings,
    upsert_settings,
    toggle_auto_schedule_db,
)

router = APIRouter(prefix="/interviews", tags=["interview-scheduling"])


@router.get("/settings", response_model=ProviderInterviewSettingsOut)
async def get_settings(
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    settings = await get_or_create_settings(db, user.id)
    return ProviderInterviewSettingsOut.model_validate(settings)


@router.put("/settings", response_model=ProviderInterviewSettingsOut)
async def update_settings(
    body: ProviderInterviewSettingsUpdate,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    if body.auto_schedule_enabled and body.windows is None:
        existing = await get_or_create_settings(db, user.id)
        if not existing.availability_windows:
            raise HTTPException(
                status_code=400,
                detail="Provide at least one availability window to enable auto-schedule",
            )
    settings = await upsert_settings(db, user.id, body)
    await db.commit()
    await db.refresh(settings)
    return ProviderInterviewSettingsOut.model_validate(settings)


@router.patch("/settings/toggle", response_model=ProviderInterviewSettingsOut)
async def toggle_auto_schedule(
    body: AutoScheduleToggle,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    settings = await toggle_auto_schedule_db(db, user.id, body.auto_schedule_enabled)
    await db.commit()
    await db.refresh(settings)
    return ProviderInterviewSettingsOut.model_validate(settings)


@router.get("/availability/preview", response_model=SlotPreviewListOut)
async def preview_slots(
    limit: int = Query(10, ge=1, le=50),
    application_id: str | None = None,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await preview_available_slots(
        db, user.id, limit=limit, application_id=application_id
    )

