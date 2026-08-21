from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.modules.jobs_portal.schemas.jobs import NotificationOut
from app.core.dependencies import require_authenticated
from app.shared.controllers.notifications_controller import (
    get_notifications as ctrl_get_notifications,
    unread_count as ctrl_unread_count,
    mark_read as ctrl_mark_read,
    mark_all_read as ctrl_mark_all_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def get_notifications(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_notifications(db=db, current_user=user)


@router.get("/unread-count")
async def unread_count(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    return await ctrl_unread_count(db=db, current_user=user)


@router.patch("/read-all")
async def mark_all_read(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    return await ctrl_mark_all_read(db=db, current_user=user)


@router.patch("/{notif_id}/read")
async def mark_read(notif_id: str, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    return await ctrl_mark_read(notification_id=notif_id, db=db, current_user=user)


@router.get("/stream/{user_id}")
@router.get("/api/stream/{user_id}")
async def stream_notifications(user_id: str, current_user: User = Depends(require_authenticated)):
    """Server-Sent Events (SSE) stream for real-time notifications with heartbeat."""
    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse
    import asyncio
    import redis.asyncio as aioredis
    from app.core.config import settings

    if str(current_user.id) != str(user_id) and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    async def event_generator():
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        pubsub = r.pubsub()
        channel = f"user_events:{user_id}"
        await pubsub.subscribe(channel)
        try:
            # Initial ping
            yield "event: ping\ndata: {}\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=15.0)
                    if message and message.get("type") == "message":
                        data = message["data"].decode("utf-8") if isinstance(message["data"], bytes) else str(message["data"])
                        yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    # 15s heartbeat ping
                    yield "event: ping\ndata: {}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
