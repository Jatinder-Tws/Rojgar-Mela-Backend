"""Help desk AI bot — REST config + WebSocket real-time chat."""

from __future__ import annotations

import base64
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import AsyncSessionLocal, get_db
from models.user import User
from services.auth_service import require_seeker_or_provider
from services.gemini_live_proxy import GeminiLiveProxy
from services.support_bot_knowledge import _support_contact
from services.support_bot_service import (
    BotChatMessage,
    escalate_session,
    get_or_create_session,
    process_text_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support/bot", tags=["help-desk-bot"])


async def _validate_ws_token(token: str, user_id: str) -> bool:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return str(payload.get("sub")) == str(user_id)
    except JWTError:
        return False


async def _get_user_from_db(user_id: str) -> Optional[User]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


@router.get("/config")
async def bot_config(user: User = Depends(require_seeker_or_provider)):
    role = user.role.value if hasattr(user.role, "value") else str(user.role or "seeker")
    return {
        "modes": [
            {"id": "voice", "label": "Voice to Voice", "description": "Speak with AI (Gemini Live, PCM 16kHz in / 24kHz out)"},
        ],
        "live_model": settings.GEMINI_LIVE_MODEL,
        "audio_input": {"format": "pcm16", "sample_rate": 16000},
        "audio_output": {"format": "pcm16", "sample_rate": 24000},
        "user_role": role,
        "support_contact": _support_contact(),
        "gemini_configured": bool(settings.GOOGLE_API_KEY),
    }


async def helpdesk_websocket_handler(
    websocket: WebSocket,
    user_id: str,
    token: str,
    mode: str = "text",
):
    await websocket.accept()

    if not await _validate_ws_token(token, user_id):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user = await _get_user_from_db(user_id)
    if not user or user.is_super_admin:
        await websocket.close(code=4003, reason="Invalid user")
        return
    user_role = user.role.value if hasattr(user.role, "value") else str(user.role or "seeker")
    chat_mode = "voice" if mode == "voice" else (mode if mode in ("text", "text_voice") else "voice")
    live_proxy: Optional[GeminiLiveProxy] = None

    async def send_json(payload: dict) -> None:
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception:
            pass

    try:
        await send_json({
            "type": "session_started",
            "mode": chat_mode,
            "user_role": user_role,
            "live_model": settings.GEMINI_LIVE_MODEL,
        })

        if chat_mode in ("voice", "text_voice"):
            if not settings.GOOGLE_API_KEY:
                await send_json({"type": "error", "message": "Voice mode requires GOOGLE_API_KEY"})
                await websocket.close()
                return

            live_proxy = GeminiLiveProxy(user_role)

            async def on_audio(chunk: bytes) -> None:
                await send_json({
                    "type": "bot_audio",
                    "data": base64.b64encode(chunk).decode("ascii"),
                    "sample_rate": 24000,
                })

            async def on_transcript(role: str, text: str) -> None:
                text_clean = (text or "").strip()
                if not text_clean:
                    return
                session = get_or_create_session(user_id, user_role)
                role_name = "user" if role == "user" else "assistant"
                if session.messages and session.messages[-1].role == role_name:
                    session.messages[-1].content = (session.messages[-1].content.strip() + " " + text_clean).strip()
                else:
                    session.messages.append(
                        BotChatMessage(
                            role=role_name,
                            content=text_clean,
                        )
                    )
                await send_json({
                    "type": "transcript",
                    "role": role_name,
                    "text": text_clean,
                })

            async def on_state(voice_state: str) -> None:
                await send_json({"type": "bot_state", "state": voice_state})

            async def on_interrupted() -> None:
                await send_json({"type": "bot_interrupted"})

            async def on_error(msg: str) -> None:
                await send_json({"type": "error", "message": msg})

            live_proxy.on_audio = on_audio
            live_proxy.on_transcript = on_transcript
            live_proxy.on_state = on_state
            live_proxy.on_interrupted = on_interrupted
            live_proxy.on_error = on_error
            await live_proxy.start()
            await send_json({"type": "bot_state", "state": "listening"})

        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except RuntimeError as exc:
                if "accept" in str(exc).lower() or "not connected" in str(exc).lower():
                    break
                raise
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await send_json({"type": "pong"})
                continue

            if msg_type == "escalate":
                async with AsyncSessionLocal() as db:
                    result = await escalate_session(user, db)
                await send_json(result)
                continue

            if msg_type == "text":
                content = (msg.get("content") or "").strip()
                if not content:
                    continue

                if chat_mode == "text":
                    await send_json({"type": "typing", "is_typing": True})
                    async with AsyncSessionLocal() as db:
                        result = await process_text_message(user, content, db)
                    await send_json({"type": "typing", "is_typing": False})
                    await send_json(result)
                elif chat_mode in ("voice", "text_voice") and live_proxy and live_proxy.is_alive:
                    await send_json({"type": "typing", "is_typing": True})
                    await live_proxy.send_text(content)
                    await send_json({"type": "typing", "is_typing": False})
                continue

            if msg_type == "audio" and live_proxy and live_proxy.is_alive and chat_mode == "voice":
                b64 = msg.get("data", "")
                if b64:
                    pcm = base64.b64decode(b64)
                    await live_proxy.send_audio_pcm16(pcm)
                continue

            if msg_type == "mode":
                new_mode = msg.get("mode", chat_mode)
                if new_mode != chat_mode:
                    await send_json({
                        "type": "error",
                        "message": "Switch mode by reconnecting with ?mode=text|voice|text_voice",
                    })
                continue

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Help desk WS error: %s", exc)
        try:
            await send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if live_proxy:
            await live_proxy.close()
