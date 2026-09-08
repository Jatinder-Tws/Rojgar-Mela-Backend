"""
Redis pub/sub for live class-session updates.

API workers and Celery both publish to ``training_class_live``; the WebSocket
route subscribes and fans out to connected training-portal clients so the UI
does not need to poll ``/class-sessions/today``.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.config import settings
from app.modules.training_portal.models.training_portal_class_session import (
    TrainingPortalClassSession,
)
from app.modules.training_portal.services.training_portal_class_live import now_ist, today_ist
from app.modules.training_portal.services.training_portal_mapper import session_to_out_for_date

logger = logging.getLogger(__name__)

CLASS_LIVE_CHANNEL = "training_class_live"


def build_class_live_event(
    session: TrainingPortalClassSession,
    event: str,
) -> dict[str, Any]:
    today = today_ist()
    now = now_ist()
    payload = session_to_out_for_date(session, today, now).model_dump(mode="json")
    return {
        "type": "CLASS_SESSION_UPDATE",
        "event": event,
        "data": payload,
    }


async def publish_class_live_event(
    session: TrainingPortalClassSession,
    event: str,
) -> None:
    await publish_class_live_payload(build_class_live_event(session, event))


async def publish_class_live_payload(message: dict[str, Any]) -> None:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        await r.publish(CLASS_LIVE_CHANNEL, json.dumps(message, default=str))
        await r.aclose()
    except Exception as exc:
        logger.warning("Failed to publish class live event: %s", exc)


def instructor_matches(filter_name: Optional[str], instructor_name: Optional[str]) -> bool:
    if not filter_name or not filter_name.strip():
        return True
    return (instructor_name or "").strip().lower() == filter_name.strip().lower()
