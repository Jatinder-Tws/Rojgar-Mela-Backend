"""
WebSocket fan-out for live class-session updates.

Auth via ``?token=`` (browsers cannot set Authorization on WS handshake).
Optional ``?instructor_name=`` filters events to one teacher; omit for all
(admin / shared panels).
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.dependencies import get_current_user_ws
from app.modules.training_portal.services.class_live_realtime import (
    CLASS_LIVE_CHANNEL,
    instructor_matches,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Training Class Live"])

WS_AUTH_FAILED = 4001


@router.websocket("/ws/training-class-live")
async def training_class_live_ws(websocket: WebSocket):
    async with AsyncSessionLocal() as db:
        user = await get_current_user_ws(websocket, db)
        if user is None:
            await websocket.close(code=WS_AUTH_FAILED)
            return
        user_id = user.id

    instructor_filter = (websocket.query_params.get("instructor_name") or "").strip()

    await websocket.accept()
    await websocket.send_json({"type": "connected", "channel": CLASS_LIVE_CHANNEL})

    r = None
    pubsub = None
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        pubsub = r.pubsub()
        await pubsub.subscribe(CLASS_LIVE_CHANNEL)

        async def pump_redis():
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message or message.get("type") != "message":
                    await asyncio.sleep(0.05)
                    continue
                raw = message.get("data")
                data_str = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                try:
                    payload = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                session_data = payload.get("data") if isinstance(payload, dict) else None
                instructor_name = (
                    session_data.get("instructor_name") if isinstance(session_data, dict) else None
                )
                if not instructor_matches(instructor_filter, instructor_name):
                    continue
                await websocket.send_text(data_str)

        async def pump_client():
            while True:
                # Client may send pongs/empty; disconnect raises WebSocketDisconnect.
                await websocket.receive_text()

        async def heartbeat():
            while True:
                await asyncio.sleep(20)
                await websocket.send_json({"type": "ping"})

        done, pending = await asyncio.wait(
            [
                asyncio.create_task(pump_redis()),
                asyncio.create_task(pump_client()),
                asyncio.create_task(heartbeat()),
            ],
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                raise exc
    except WebSocketDisconnect:
        logger.info(
            "Training class live WS disconnected (user_id=%s, instructor_filter=%s)",
            user_id,
            instructor_filter or "*",
        )
    except Exception as exc:
        logger.warning("Training class live WS error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        try:
            if pubsub is not None:
                await pubsub.unsubscribe(CLASS_LIVE_CHANNEL)
                await pubsub.aclose()
        except Exception:
            pass
        try:
            if r is not None:
                await r.aclose()
        except Exception:
            pass
