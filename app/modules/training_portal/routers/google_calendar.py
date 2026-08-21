"""Google Calendar connect/disconnect endpoints for the training portal.

Per-user OAuth so teachers and students can opt into automatic sync of their
class schedule into their own Google Calendar. If OAuth is not configured, the
status endpoint reports it and the connect flow is disabled (ICS email invites
still work independently).
"""

import logging
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.shared.models.user import User
from app.modules.training_portal.models.google_calendar_token import GoogleCalendarToken
from app.core.dependencies import require_training_portal_user
from app.modules.training_portal.services import google_calendar_service as gcal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google-calendar", tags=["Google Calendar"])

_STATE_PURPOSE = "gcal_connect"


def _create_state(user_id: str) -> str:
    payload = {
        "sub": str(user_id),
        "purpose": _STATE_PURPOSE,
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_state(state: str) -> str:
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc
    if payload.get("purpose") != _STATE_PURPOSE or not payload.get("sub"):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    return str(payload["sub"])


def _post_connect_url() -> str:
    base = settings.GOOGLE_CALENDAR_POST_CONNECT_URL or settings.TRAINING_URL
    return base.rstrip("/")


@router.get("/status")
async def google_calendar_status(
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GoogleCalendarToken).where(GoogleCalendarToken.user_id == str(current_user.id))
    )
    token = result.scalar_one_or_none()
    connected = bool(token and token.refresh_token)
    return {
        "configured": gcal.is_configured(),
        "connected": connected,
        "google_email": token.google_email if connected else None,
    }


@router.get("/connect")
async def google_calendar_connect(
    current_user: User = Depends(require_training_portal_user),
):
    if not gcal.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google Calendar integration is not configured on the server.",
        )
    state = _create_state(str(current_user.id))
    return {"authorization_url": gcal.build_authorization_url(state)}


@router.get("/callback")
async def google_calendar_callback(
    state: str = Query(...),
    code: str | None = Query(None),
    error: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    redirect_base = _post_connect_url()

    if error or not code:
        return RedirectResponse(f"{redirect_base}/?{urlencode({'gcal': 'error'})}")

    try:
        user_id = _decode_state(state)
    except HTTPException:
        return RedirectResponse(f"{redirect_base}/?{urlencode({'gcal': 'error'})}")

    try:
        payload = await gcal.exchange_code(code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Google token exchange failed: %s", exc)
        return RedirectResponse(f"{redirect_base}/?{urlencode({'gcal': 'error'})}")

    google_email = None
    if payload.get("access_token"):
        google_email = await gcal.fetch_userinfo_email(payload["access_token"])

    result = await db.execute(
        select(GoogleCalendarToken).where(GoogleCalendarToken.user_id == user_id)
    )
    token = result.scalar_one_or_none()
    if not token:
        token = GoogleCalendarToken(id=str(uuid.uuid4()), user_id=user_id)
        db.add(token)
    gcal.store_tokens(token, payload, google_email)
    await db.commit()

    status_flag = "connected" if token.refresh_token else "error"
    return RedirectResponse(f"{redirect_base}/?{urlencode({'gcal': status_flag})}")


@router.post("/disconnect")
async def google_calendar_disconnect(
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GoogleCalendarToken).where(GoogleCalendarToken.user_id == str(current_user.id))
    )
    token = result.scalar_one_or_none()
    if token:
        await db.delete(token)
        await db.commit()
    return {"connected": False}
