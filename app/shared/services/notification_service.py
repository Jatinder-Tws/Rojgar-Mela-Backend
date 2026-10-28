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
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
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
    auto_commit: bool = False,
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

    if auto_commit:
        await db.commit()

    # Stream event via SSE (wrapped in type: NOTIFICATION so frontend notification handlers catch it)
    payload = {
        "id": str(notif.id),
        "user_id": str(notif.user_id),
        "title": notif.title,
        "message": notif.message,
        "type": notif.type.value if hasattr(notif.type, "value") else str(notif.type),
        "is_read": False,
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
        "related_job_id": notif.related_job_id,
        "related_user_id": notif.related_user_id,
    }
    await _publish_sse_event(str(user_id), {
        "type": "NOTIFICATION",
        "data": payload,
    })

    return notif


async def notify_super_admins(
    db: AsyncSession,
    title: str,
    message: str,
    type: NotificationType = NotificationType.general,
    related_job_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
    auto_commit: bool = True,
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
            auto_commit=False,
        )
    if auto_commit and admin_ids:
        await db.commit()
