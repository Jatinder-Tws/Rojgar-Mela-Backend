from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.jobs import NotificationOut
from services.auth_service import require_verified
from controllers.notifications_controller import (
    get_notifications as ctrl_get_notifications,
    unread_count as ctrl_unread_count,
    mark_read as ctrl_mark_read,
    mark_all_read as ctrl_mark_all_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def get_notifications(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_notifications(user, db)


@router.get("/unread-count")
async def unread_count(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_unread_count(user, db)


@router.patch("/{notif_id}/read")
async def mark_read(notif_id: str, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_mark_read(notif_id, user, db)


@router.patch("/read-all")
async def mark_all_read(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_mark_all_read(user, db)
