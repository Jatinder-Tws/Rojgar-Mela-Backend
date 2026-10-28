"""Redis pub/sub for AI screening progress (Celery publishes → API WS fans out)."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

SCREENING_PROGRESS_CHANNEL = "ai_screening_progress"


def screening_channel_for_batch(batch_id: str) -> str:
    return f"{SCREENING_PROGRESS_CHANNEL}:{batch_id}"


async def publish_screening_progress(batch_id: str, payload: dict[str, Any]) -> None:
    """Publish a progress snapshot for one batch. Safe no-op if Redis is down."""
    message = {
        "type": "SCREENING_PROGRESS",
        "batch_id": str(batch_id),
        "data": payload,
    }
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        await r.publish(screening_channel_for_batch(batch_id), json.dumps(message, default=str))
        await r.aclose()
    except Exception as exc:
        logger.warning("Failed to publish screening progress for %s: %s", batch_id, exc)


def progress_payload_from_batch(batch) -> dict[str, Any]:
    total = batch.total_files or 0
    pending = max(
        0,
        total
        - (batch.matched_count or 0)
        - (batch.failed_count or 0)
        - (batch.skipped_count or 0),
    )
    return {
        "batch_id": str(batch.id),
        "status": batch.status,
        "current_stage": batch.current_stage,
        "progress_percent": float(batch.progress_percent or 0),
        "total_files": total,
        "uploaded_count": batch.uploaded_count or 0,
        "parsed_count": batch.parsed_count or 0,
        "matched_count": batch.matched_count or 0,
        "failed_count": batch.failed_count or 0,
        "skipped_count": batch.skipped_count or 0,
        "pending_count": pending,
        "error_summary": batch.error_summary,
    }
