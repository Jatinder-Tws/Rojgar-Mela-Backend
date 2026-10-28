"""WebSocket fan-out for AI Resume Screening batch progress."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.dependencies import get_current_user_ws
from app.modules.jobs_portal.models.screening import ScreeningBatch
from app.modules.jobs_portal.services.screening_realtime import (
    progress_payload_from_batch,
    screening_channel_for_batch,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-screening-ws"])
WS_AUTH_FAILED = 4001
WS_FORBIDDEN = 4003


@router.websocket("/ws/ai-screening/{batch_id}")
async def screening_progress_ws(websocket: WebSocket, batch_id: str):
    async with AsyncSessionLocal() as db:
        user = await get_current_user_ws(websocket, db)
        if user is None:
            await websocket.close(code=WS_AUTH_FAILED)
            return
        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        if role_val != "provider":
            await websocket.close(code=WS_FORBIDDEN)
            return

        res = await db.execute(
            select(ScreeningBatch).where(
                ScreeningBatch.id == batch_id,
                ScreeningBatch.provider_id == user.id,
            )
        )
        batch = res.scalar_one_or_none()
        if not batch:
            await websocket.close(code=WS_FORBIDDEN)
            return
        snapshot = progress_payload_from_batch(batch)

    await websocket.accept()
    await websocket.send_json({"type": "connected", "batch_id": batch_id, "data": snapshot})

    # If already terminal, send final and keep connection until client leaves
    terminal = snapshot.get("status") in ("completed", "partial", "failed", "cancelled")

    r = None
    pubsub = None
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        pubsub = r.pubsub()
        channel = screening_channel_for_batch(batch_id)
        await pubsub.subscribe(channel)

        async def pump_redis():
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message or message.get("type") != "message":
                    await asyncio.sleep(0.05)
                    continue
                raw = message.get("data")
                data_str = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                await websocket.send_text(data_str)
                try:
                    payload = json.loads(data_str)
                    status = (payload.get("data") or {}).get("status")
                    if status in ("completed", "partial", "failed", "cancelled"):
                        # Keep open briefly so client can apply final state; client closes.
                        await asyncio.sleep(0.5)
                except json.JSONDecodeError:
                    pass

        async def pump_client():
            while True:
                await websocket.receive_text()

        async def heartbeat():
            while True:
                await asyncio.sleep(20)
                await websocket.send_json({"type": "ping"})

        tasks = [
            asyncio.create_task(pump_redis()),
            asyncio.create_task(pump_client()),
            asyncio.create_task(heartbeat()),
        ]
        if terminal:
            # Still listen in case of late events; snapshot already sent
            pass

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                raise exc
    except WebSocketDisconnect:
        logger.info("Screening WS disconnected batch_id=%s", batch_id)
    except Exception as exc:
        logger.warning("Screening WS error batch_id=%s: %s", batch_id, exc)
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        try:
            if pubsub is not None:
                await pubsub.unsubscribe(screening_channel_for_batch(batch_id))
                await pubsub.aclose()
        except Exception:
            pass
        try:
            if r is not None:
                await r.aclose()
        except Exception:
            pass
