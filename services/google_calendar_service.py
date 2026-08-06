"""Google Calendar OAuth + event CRUD for per-user class schedule auto-sync.

OAuth token exchange/refresh is done with httpx (async, no extra deps). Calendar
API calls use google-api-python-client (sync) wrapped in a thread so they don't
block the event loop. All of this is optional: if OAuth is not configured the
callers simply skip it and rely on ICS email invites instead.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.google_calendar_token import GoogleCalendarToken
from models.training_portal_class_session import TrainingPortalClassSession
from models.training_portal_batch import TrainingPortalBatch
from services import class_calendar_common as cc

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "email",
]
_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


def is_configured() -> bool:
    return settings.google_calendar_oauth_configured()


def build_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return f"{_AUTH_ENDPOINT}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """Exchange an authorization code for tokens."""
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
        "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(_TOKEN_ENDPOINT, data=data)
        resp.raise_for_status()
        return resp.json()


async def fetch_userinfo_email(access_token: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                _USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json().get("email")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Google userinfo fetch failed: %s", exc)
        return None


async def _refresh_access_token(row: GoogleCalendarToken) -> Optional[str]:
    if not row.refresh_token:
        return None
    data = {
        "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
        "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
        "refresh_token": row.refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(_TOKEN_ENDPOINT, data=data)
        resp.raise_for_status()
        payload = resp.json()
    access_token = payload.get("access_token")
    expires_in = int(payload.get("expires_in", 3600))
    row.access_token = access_token
    row.expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    row.updated_at = datetime.utcnow()
    return access_token


async def ensure_access_token(db: AsyncSession, row: GoogleCalendarToken) -> Optional[str]:
    """Return a currently-valid access token, refreshing (and persisting) if needed."""
    now = datetime.utcnow()
    if row.access_token and row.expiry and row.expiry - timedelta(seconds=60) > now:
        return row.access_token
    token = await _refresh_access_token(row)
    if token:
        await db.flush()
    return token


def store_tokens(row: GoogleCalendarToken, payload: dict, google_email: Optional[str]) -> None:
    """Populate a token row from a token-endpoint payload (create or update)."""
    if payload.get("access_token"):
        row.access_token = payload["access_token"]
    # Google only returns refresh_token on first consent; keep the existing one otherwise.
    if payload.get("refresh_token"):
        row.refresh_token = payload["refresh_token"]
    expires_in = int(payload.get("expires_in", 3600))
    row.expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    row.scopes = payload.get("scope") or " ".join(SCOPES)
    row.token_uri = _TOKEN_ENDPOINT
    if google_email:
        row.google_email = google_email
    row.updated_at = datetime.utcnow()


def build_event_body(
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
) -> Optional[dict]:
    dts = cc.session_datetimes(session, batch)
    if not dts:
        return None
    start_dt, end_dt = dts
    body: dict = {
        "summary": cc.event_summary(session),
        "location": cc.event_location(session, batch),
        "description": cc.event_description(session, batch),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": cc.IANA_TZ},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": cc.IANA_TZ},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "popup", "minutes": 15},
            ],
        },
    }
    rrule = cc.recurrence_rule(session, batch)
    if rrule:
        body["recurrence"] = [f"RRULE:{rrule}"]
    return body


def _calendar_service(access_token: str):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(token=access_token)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _upsert_event_sync(access_token: str, calendar_id: str, body: dict, event_id: Optional[str]) -> str:
    service = _calendar_service(access_token)
    if event_id:
        try:
            updated = service.events().update(
                calendarId=calendar_id, eventId=event_id, body=body
            ).execute()
            return updated["id"]
        except Exception as exc:  # noqa: BLE001
            # Event was deleted on Google's side — recreate it.
            logger.info("Calendar event update failed, recreating: %s", exc)
    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    return created["id"]


def _delete_event_sync(access_token: str, calendar_id: str, event_id: str) -> None:
    service = _calendar_service(access_token)
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.info("Calendar event delete skipped: %s", exc)


async def upsert_event(
    access_token: str,
    body: dict,
    *,
    calendar_id: str = "primary",
    event_id: Optional[str] = None,
) -> str:
    return await asyncio.to_thread(_upsert_event_sync, access_token, calendar_id, body, event_id)


async def delete_event(
    access_token: str,
    event_id: str,
    *,
    calendar_id: str = "primary",
) -> None:
    await asyncio.to_thread(_delete_event_sync, access_token, calendar_id, event_id)
