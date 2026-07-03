"""Helpers for live class sessions, reminders, and attendance."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from models.training_portal_class_session import TrainingPortalClassSession

REMINDER_MINUTES_BEFORE = 30


def _parse_time_12h(value: str) -> Optional[time]:
    raw = (value or "").strip()
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def session_occurs_on_date(session: TrainingPortalClassSession, target: date) -> bool:
    if session.postponed or session.teacher_unavailable:
        return False
    if session.schedule_type == "recurring":
        if not session.days:
            return False
        day_abbr = target.strftime("%a")
        return day_abbr in (session.days or [])
    return session.date == target.isoformat()


def session_start_datetime(session: TrainingPortalClassSession, target: date) -> Optional[datetime]:
    parsed = _parse_time_12h(session.start_time)
    if not parsed:
        return None
    return datetime.combine(target, parsed)


def session_end_datetime(session: TrainingPortalClassSession, target: date) -> Optional[datetime]:
    parsed = _parse_time_12h(session.end_time)
    if not parsed:
        return None
    return datetime.combine(target, parsed)


def minutes_until_start(session: TrainingPortalClassSession, now: datetime, target: date) -> Optional[float]:
    start = session_start_datetime(session, target)
    if not start:
        return None
    return (start - now).total_seconds() / 60.0


def should_show_start_button(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    if session.live_status != "scheduled":
        return False
    start = session_start_datetime(session, target)
    if not start:
        return False
    return now >= start


def should_send_reminder(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    if session.reminder_sent or session.live_status == "completed":
        return False
    mins = minutes_until_start(session, now, target)
    if mins is None:
        return False
    return 0 < mins <= REMINDER_MINUTES_BEFORE


def format_duration(seconds: int) -> str:
    hours, rem = divmod(max(0, seconds), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes:02d}m {secs:02d}s"


def elapsed_class_seconds(started_at: Optional[datetime], now: Optional[datetime] = None) -> int:
    if not started_at:
        return 0
    end = now or datetime.utcnow()
    return int((end - started_at).total_seconds())
