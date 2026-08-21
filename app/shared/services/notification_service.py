import json
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.shared.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


async def _publish_sse_event(user_id: str, data: dict):
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.publish(f"user_events:{user_id}", json.dumps(data))
        await r.aclose()
    except Exception as e:
        logger.warning(f"Failed to publish SSE event: {e}")


async def create_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    type: NotificationType = NotificationType.general,
    related_job_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
    email_notification: bool = False,
    **kwargs,
) -> Notification:
    """Create and persist a notification record."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        related_job_id=related_job_id,
        related_user_id=related_user_id,
    )
    db.add(notif)
    await db.flush()

    # Stream event via SSE
    await _publish_sse_event(str(user_id), {
        "id": str(notif.id),
        "title": notif.title,
        "message": notif.message,
        "type": notif.type.value if hasattr(notif.type, "value") else str(notif.type),
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
    })

    return notif


async def notify_super_admins(
    db: AsyncSession,
    title: str,
    message: str,
    type: NotificationType = NotificationType.general,
    related_job_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
):
    """Notify all super admin users in the system."""
    from app.shared.models.user import User

    res = await db.execute(select(User.id).where(User.is_super_admin.is_(True)))
    admin_ids = res.scalars().all()
    for aid in admin_ids:
        await create_notification(
            db,
            user_id=aid,
            title=title,
            message=message,
            type=type,
            related_job_id=related_job_id,
            related_user_id=related_user_id,
        )
