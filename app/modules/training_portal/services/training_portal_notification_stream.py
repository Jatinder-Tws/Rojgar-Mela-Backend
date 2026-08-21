"""
Pushes newly created TrainingPortalCandidateNotification rows onto the same Redis
pub/sub channel (``user_events:{user_id}``) that the shared SSE endpoint
(``/api/notifications/stream/{user_id}``, app/shared/routers/notifications.py) reads
from, so training-portal notifications (attendance marks, batch updates, leave
status, etc.) reach the frontend in real time instead of only via polling.

There are 30+ call sites across training_portal_runtime.py and
training_portal_class_lifecycle.py that construct TrainingPortalCandidateNotification
directly (`db.add(TrainingPortalCandidateNotification(...))`). Rather than adding a
publish call at every site (easy to miss on future additions), this module hooks the
ORM layer once: any row inserted into this table gets queued during flush and
published after the enclosing transaction actually commits.

Importing this module registers the listeners as a side effect — it must be
imported once during app startup (see app/main.py).
"""

import asyncio
import json
import logging

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, object_session

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.shared.models.user import User
from app.modules.training_portal.models.training_portal_candidate_notification import (
    TrainingPortalCandidateNotification,
)
from app.modules.training_portal.services.training_portal_mapper import notification_to_out

logger = logging.getLogger(__name__)

_PENDING_KEY = "_pending_training_notification_sse"


@event.listens_for(TrainingPortalCandidateNotification, "after_insert")
def _queue_notification_for_sse(mapper, connection, target: TrainingPortalCandidateNotification) -> None:
    session = object_session(target)
    if session is None:
        return
    # Build the JSON-safe payload now, while the freshly-flushed row is guaranteed
    # populated, instead of holding a reference to the ORM object until after commit.
    payload = notification_to_out(target).model_dump(mode="json")
    session.info.setdefault(_PENDING_KEY, []).append(payload)


@event.listens_for(Session, "after_commit")
def _dispatch_queued_notifications(session: Session) -> None:
    pending = session.info.pop(_PENDING_KEY, None)
    if not pending:
        return
    for payload in pending:
        try:
            asyncio.create_task(_publish_notification(payload))
        except RuntimeError:
            # No running event loop (e.g. a standalone/sync script) — the
            # notification is still persisted; it'll just show up on next poll.
            logger.debug("No running event loop; skipping SSE publish for %s", payload.get("id"))


async def _publish_notification(payload: dict) -> None:
    email = (payload.get("candidate_email") or "").strip().lower()
    if not email:
        return
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User.id).where(func.lower(User.email) == email))
            user_id = result.scalar_one_or_none()
        if not user_id:
            return

        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        await r.publish(
            f"user_events:{user_id}",
            json.dumps({"type": "NOTIFICATION", "data": payload}),
        )
        await r.aclose()
    except Exception as exc:
        logger.warning("Failed to publish training notification SSE event: %s", exc)
