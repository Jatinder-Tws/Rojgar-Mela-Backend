from fastapi import HTTPException
from sqlalchemy import select, func, update, not_, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.models.notification import Notification
from app.shared.models.user import User
from app.modules.super_admin.models.support_ticket import SupportTicket


def _training_notification_condition():
    """Matches training-specific notification rows so Job Portal stays clean."""
    training_title_conds = [
        Notification.title.ilike("%enrollment%"),
        Notification.title.ilike("%batch preference%"),
        Notification.title.ilike("%batch assigned%"),
        Notification.title.ilike("%batch full%"),
        Notification.title.ilike("%class session%"),
        Notification.title.ilike("%class schedule%"),
        Notification.title.ilike("%class reminder%"),
        Notification.title.ilike("%class update%"),
        Notification.title.ilike("%class ending%"),
        Notification.title.ilike("%class ended%"),
        Notification.title.ilike("%attendance marked%"),
        Notification.title.ilike("%refund request%"),
        Notification.title.ilike("%refund status%"),
        Notification.title.ilike("%student leave%"),
        Notification.title.ilike("%teacher leave%"),
        Notification.title.ilike("%behavior report%"),
        Notification.title.ilike("%behavior star%"),
    ]
    training_ticket_ids = select(SupportTicket.id).where(SupportTicket.source == "training")
    return or_(
        *training_title_conds,
        and_(
            Notification.related_job_id.isnot(None),
            Notification.related_job_id.in_(training_ticket_ids),
        ),
    )


async def get_notifications(db: AsyncSession, current_user: User):
    result = await db.execute(
        select(Notification)
        .where(
            Notification.user_id == current_user.id,
            not_(_training_notification_condition()),
        )
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
            Notification.is_read.is_(False),
            not_(_training_notification_condition()),
        )
    )
    count = int(result.scalar() or 0)
    return {
        "unread_count": count,
        "count": count,
    }
