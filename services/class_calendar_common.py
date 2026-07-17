"""Shared helpers to turn a training class session into calendar event fields.

Used by both the ICS invite builder and the Google Calendar API sync so that
emailed invites and API-pushed events stay identical.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from models.training_portal_class_session import TrainingPortalClassSession
from models.training_portal_batch import TrainingPortalBatch
from services.training_portal_class_live import _parse_time_12h, today_ist

IST_TZ = timezone(timedelta(hours=5, minutes=30))
IANA_TZ = "Asia/Kolkata"

# Class session `days` use %a abbreviations ("Mon", "Tue", ...).
_WEEKDAY_TO_RRULE = {
    "Mon": "MO",
    "Tue": "TU",
    "Wed": "WE",
    "Thu": "TH",
    "Fri": "FR",
    "Sat": "SA",
    "Sun": "SU",
}


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except (ValueError, AttributeError):
        return None


def first_occurrence_date(
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
) -> date:
    """Date of the first occurrence used as the anchor for the calendar event."""
    if session.schedule_type != "recurring":
        return _parse_iso_date(session.date) or today_ist()

    days = session.days or []
    window_start = (
        _parse_iso_date(batch.start_date if batch else None)
        or _parse_iso_date(session.date)
        or today_ist()
    )
    if not days:
        return window_start
    # Walk forward up to a week to land on the first matching weekday.
    for offset in range(0, 7):
        candidate = window_start + timedelta(days=offset)
        if candidate.strftime("%a") in days:
            return candidate
    return window_start


def session_datetimes(
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
) -> Optional[tuple[datetime, datetime]]:
    """Naive IST (start, end) datetimes for the anchor occurrence, or None if unparseable."""
    start_t = _parse_time_12h(session.start_time)
    end_t = _parse_time_12h(session.end_time)
    if not start_t or not end_t:
        return None
    anchor = first_occurrence_date(session, batch)
    start_dt = datetime.combine(anchor, start_t)
    end_dt = datetime.combine(anchor, end_t)
    if end_dt <= start_dt:
        # Guard against equal/reversed times so events have positive duration.
        end_dt = start_dt + timedelta(hours=1)
    return start_dt, end_dt


def recurrence_rule(
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
) -> Optional[str]:
    """RRULE string (without the 'RRULE:' prefix) for recurring sessions, else None."""
    if session.schedule_type != "recurring":
        return None
    days = session.days or []
    byday = [_WEEKDAY_TO_RRULE[d] for d in days if d in _WEEKDAY_TO_RRULE]
    if not byday:
        return None
    rule = f"FREQ=WEEKLY;BYDAY={','.join(byday)}"
    end_date = _parse_iso_date(batch.end_date if batch else None)
    if end_date:
        # UNTIL is inclusive; use end of day in IST converted to UTC.
        until_ist = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=IST_TZ)
        until_utc = until_ist.astimezone(timezone.utc)
        rule += f";UNTIL={until_utc.strftime('%Y%m%dT%H%M%SZ')}"
    return rule


def event_summary(session: TrainingPortalClassSession) -> str:
    return f"Class: {session.title}"


def event_location(
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
) -> str:
    return session.venue or (batch.venue if batch else "") or "To be announced"


def event_description(
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
) -> str:
    lines = [
        f"Training class: {session.title}",
        f"Instructor: {session.instructor_name}",
        f"Time: {session.start_time} - {session.end_time} (IST)",
    ]
    if batch and batch.batch_name:
        lines.append(f"Batch: {batch.batch_name}")
    location = event_location(session, batch)
    if location:
        lines.append(f"Venue: {location}")
    if session.note:
        lines.append("")
        lines.append(session.note)
    lines.append("")
    lines.append("Scheduled via RojgarMela Training Portal.")
    return "\n".join(lines)


def event_uid(session_id: str, sender_domain: str) -> str:
    """Stable UID so update/cancel invites replace the original calendar entry."""
    return f"rojgarmela-class-{session_id}@{sender_domain}"
