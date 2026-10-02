from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin_or_permission
from app.modules.jobs_portal.controllers import event_lucky_controller as ctrl
from app.shared.models.user import User

public_router = APIRouter(prefix="/lucky-events", tags=["lucky-events"])
admin_router = APIRouter(prefix="/super-admin/lucky-draw", tags=["lucky-draw"])


class RegisterIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=150)
    phone: str = Field(..., min_length=10, max_length=20)
    location: str = Field(..., min_length=2, max_length=250)
    role: Literal["seeker", "provider"] = "seeker"
    organization: str = Field(..., min_length=2, max_length=200)
    track: Literal["tech", "non_tech"]
    photo: str = Field(..., min_length=30, max_length=4_000_000)


class PendingIn(BaseModel):
    pending_id: str
    otp: Optional[str] = None


@public_router.get("/{slug}/live")
async def public_live(slug: str, db: AsyncSession = Depends(get_db)):
    return await ctrl.public_live(slug, db)


@public_router.get("/{slug}")
async def public_event(slug: str, db: AsyncSession = Depends(get_db)):
    return await ctrl.get_public_event(slug, db)


@public_router.post("/{slug}/register", status_code=201)
async def register(slug: str, body: RegisterIn, db: AsyncSession = Depends(get_db)):
    return await ctrl.register(slug, body, db)


@public_router.post("/{slug}/verify")
async def verify(slug: str, body: PendingIn, db: AsyncSession = Depends(get_db)):
    return await ctrl.verify(slug, body.pending_id, body.otp or "", db)


@public_router.post("/{slug}/resend")
async def resend(slug: str, body: PendingIn, db: AsyncSession = Depends(get_db)):
    return await ctrl.resend(slug, body.pending_id, db)


@public_router.post("/{slug}/reveal")
async def reveal(slug: str, db: AsyncSession = Depends(get_db)):
    return await ctrl.reveal(slug, db)


@admin_router.get("/people")
async def people(role: str = Query("seeker"), _admin: User = Depends(require_super_admin_or_permission("announcements")), db: AsyncSession = Depends(get_db)):
    if role not in {"seeker", "provider"}:
        role = "seeker"
    return await ctrl.list_people(role, db)


@admin_router.get("/winner")
async def winner(email: str, _admin: User = Depends(require_super_admin_or_permission("announcements")), db: AsyncSession = Depends(get_db)):
    return await ctrl.winner_for_email(email, db)


@admin_router.get("/{announcement_id}/entries")
async def entries(announcement_id: str, _admin: User = Depends(require_super_admin_or_permission("announcements")), db: AsyncSession = Depends(get_db)):
    return await ctrl.list_entries(announcement_id, db)


class StageIn(BaseModel):
    action: Literal["open", "spin", "close"]


@admin_router.post("/{announcement_id}/stage")
async def stage(announcement_id: str, body: StageIn, _admin: User = Depends(require_super_admin_or_permission("announcements")), db: AsyncSession = Depends(get_db)):
    return await ctrl.publish_stage(announcement_id, body.action, db)


@admin_router.post("/{announcement_id}/reveal")
async def admin_reveal(announcement_id: str, _admin: User = Depends(require_super_admin_or_permission("announcements")), db: AsyncSession = Depends(get_db)):
    return await ctrl.admin_reveal(announcement_id, db)


ws_router = APIRouter(tags=["lucky-draw-live"])


@ws_router.websocket("/ws/lucky-draw/{slug}")
async def lucky_draw_live(websocket: WebSocket, slug: str):
    import asyncio
    import json

    import redis.asyncio as aioredis

    from app.core.config import settings
    from app.core.database import AsyncSessionLocal

    await websocket.accept()
    async with AsyncSessionLocal() as db:
        current = await ctrl.public_live(slug, db)
    if isinstance(current, dict):
        current.setdefault("slug", slug)
        await websocket.send_json(current)

    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2.0)
    pubsub = redis.pubsub()
    await pubsub.subscribe(ctrl.LUCKY_STAGE_CHANNEL)

    async def pump():
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message or message.get("type") != "message":
                await asyncio.sleep(0.05)
                continue
            raw = message.get("data")
            text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if payload.get("slug") != slug:
                continue
            await websocket.send_json(payload)

    try:
        await asyncio.gather(pump(), websocket.receive_text())
    except WebSocketDisconnect:
        return
    finally:
        await pubsub.unsubscribe(ctrl.LUCKY_STAGE_CHANNEL)
        await pubsub.close()
        await redis.close()
