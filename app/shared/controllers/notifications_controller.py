from fastapi import HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.models.notification import Notification
from app.shared.models.user import User


async def get_notifications(db: AsyncSession, current_user: User):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return result.scalars().all()


async def mark_as_read(notification_id: str, db: AsyncSession, current_user: User):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    return {"message": "Notification marked as read"}

mark_read = mark_as_read


async def mark_all_read(db: AsyncSession, current_user: User):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id)
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}


async def unread_count(db: AsyncSession, current_user: User):
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False)
        )
    )
    return {"unread_count": result.scalar() or 0}
