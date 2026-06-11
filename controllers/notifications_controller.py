from typing import List
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification
from models.user import User
from schemas.jobs import NotificationOut


async def get_notifications(user: User, db: AsyncSession) -> List[NotificationOut]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.is_read.asc(), Notification.created_at.desc())
        .limit(50)
    )
    return [NotificationOut.model_validate(n) for n in result.scalars().all()]


async def unread_count(user: User, db: AsyncSession) -> dict:
    from sqlalchemy import func, select as sel
    result = await db.execute(
        sel(func.count()).where(Notification.user_id == user.id, Notification.is_read == False)  # noqa
    )
    count = result.scalar() or 0
    return {"count": count}


async def mark_read(notif_id: str, user: User, db: AsyncSession) -> dict:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    return {"ok": True}


async def mark_all_read(user: User, db: AsyncSession) -> dict:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)  # noqa
        .values(is_read=True)
    )
    await db.commit()
    return {"ok": True}
