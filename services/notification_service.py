import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification, NotificationType
from services.websocket_manager import manager
from services.email_service import send_notification_email
from schemas.jobs import NotificationOut

logger = logging.getLogger(__name__)

async def create_notification(
    db: AsyncSession,
    user_id: str,
    type: NotificationType,
    title: str,
    message: str,
    related_job_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
    email_notification: bool = True
):
    """
    Centralized service to:
    1. Create notification in DB
    2. Broadcast via WebSocket (Real-time)
    3. Send email asynchronously (Background)
    """
    try:
        # 1. Store in DB
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            related_job_id=related_job_id,
            related_user_id=related_user_id,
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)

        # 2. Broadcast via WebSocket
        notif_data = NotificationOut.model_validate(notif).model_dump()
        # Convert datetime to ISO string for JSON serialization
        notif_data["created_at"] = notif.created_at.isoformat()
        
        await manager.send_personal_message(
            {"type": "NOTIFICATION", "data": notif_data},
            str(user_id)
        )

        # 3. Send Email
        if email_notification:
            from models.user import User
            from sqlalchemy import select
            
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                # We skip awaiting email here if called from a router that doesn't use background tasks,
                # but better to let the caller handle background tasks if they want true async email.
                # For now, we'll try to send it (aiosmtplib is async).
                try:
                    await send_notification_email(user.email, user.first_name, title, message)
                except Exception as e:
                    logger.warning(f"Failed to send email notification to {user.email}: {e}")

        return notif

    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        await db.rollback()
        raise e
