"""Helpers for live class sessions, reminders, and attendance."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Optional

from models.training_portal_class_session import TrainingPortalClassSession

REMINDER_30_MINUTES_BEFORE = 30
REMINDER_15_MINUTES_BEFORE = 15
LATE_START_GRACE_MINUTES = 5
EARLY_END_GRACE_MINUTES = 5

# Class times are stored as local IST wall-clock strings ("3:30 PM"), so all
# live-session comparisons must use IST regardless of the server's timezone.
IST_TZ = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """Current IST time as a naive datetime (comparable with parsed class times)."""
    return datetime.now(IST_TZ).replace(tzinfo=None)


def today_ist() -> date:
    return now_ist().date()

ReminderTier = Literal[30, 15]


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
    end = datetime.combine(target, parsed)
    start = session_start_datetime(session, target)
    # Overnight classes (e.g. 11:00 PM – 1:00 AM): end is on the next calendar day.
    if start and end <= start:
        end = end + timedelta(days=1)
    return end


def minutes_until_end(session: TrainingPortalClassSession, now: datetime, target: date) -> Optional[float]:
    end = session_end_datetime(session, target)
    if not end:
        return None
    return (end - now).total_seconds() / 60.0


def should_send_end_reminder(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    if (getattr(session, "live_status", None) or "").strip().lower() != "live":
        return False
    if bool(getattr(session, "end_reminder_sent", False)):
        return False
    mins = minutes_until_end(session, now, target)
    if mins is None:
        return False
    return 0 < mins <= REMINDER_15_MINUTES_BEFORE


def should_auto_end_live_session(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    if (getattr(session, "live_status", None) or "").strip().lower() != "live":
        return False
    mins = minutes_until_end(session, now, target)
    if mins is None:
        return False
    return mins <= 0


def minutes_until_start(session: TrainingPortalClassSession, now: datetime, target: date) -> Optional[float]:
    start = session_start_datetime(session, target)
    if not start:
        return None
    return (start - now).total_seconds() / 60.0


def session_live_applies_to_date(session: TrainingPortalClassSession, target: date) -> bool:
    occ = (getattr(session, "live_occurrence_date", None) or "").strip()
    return occ == target.isoformat()


def effective_live_status(
    session: TrainingPortalClassSession,
    now: datetime,
    target: date,
) -> str:
    """Per-day live status — recurring sessions reset when the occurrence date changes."""
    stored = (getattr(session, "live_status", None) or "scheduled").strip().lower()
    if not session_live_applies_to_date(session, target):
        return "missed" if is_session_missed(session, now, target) else "scheduled"
    if stored in {"live", "completed"}:
        return stored
    if is_session_missed(session, now, target):
        return "missed"
    return "scheduled"


def is_session_missed(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    if session.postponed or session.teacher_unavailable:
        return False
    if not session_occurs_on_date(session, target):
        return False
    status = (getattr(session, "live_status", None) or "scheduled").strip().lower()
    if session_live_applies_to_date(session, target) and status in {"live", "completed"}:
        return False
    end = session_end_datetime(session, target)
    if not end:
        return False
    return now > end


def should_show_start_button(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    if effective_live_status(session, now, target) != "scheduled":
        return False
    start = session_start_datetime(session, target)
    end = session_end_datetime(session, target)
    if not start:
        return False
    if now < start:
        return False
    if end and now > end:
        return False
    return True


def is_late_start(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    if not should_show_start_button(session, now, target):
        return False
    start = session_start_datetime(session, target)
    if not start:
        return False
    return now > start + timedelta(minutes=LATE_START_GRACE_MINUTES)


def is_early_end(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    end = session_end_datetime(session, target)
    if not end:
        return False
    return now < end - timedelta(minutes=EARLY_END_GRACE_MINUTES)


def pending_reminder_tier(session: TrainingPortalClassSession, now: datetime, target: date) -> Optional[ReminderTier]:
    if effective_live_status(session, now, target) in {"completed", "missed"}:
        return None
    mins = minutes_until_start(session, now, target)
    if mins is None or mins <= 0:
        return None
    if mins <= REMINDER_15_MINUTES_BEFORE and not bool(getattr(session, "reminder_15_sent", False)):
        return 15
    if mins <= REMINDER_30_MINUTES_BEFORE and not bool(getattr(session, "reminder_sent", False)):
        return 30
    return None


def should_send_reminder(session: TrainingPortalClassSession, now: datetime, target: date) -> bool:
    return pending_reminder_tier(session, now, target) is not None


def format_duration(seconds: int) -> str:
    hours, rem = divmod(max(0, seconds), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes:02d}m {secs:02d}s"


def elapsed_class_seconds(started_at: Optional[datetime], now: Optional[datetime] = None) -> int:
    if not started_at:
        return 0
    end = now or now_ist()
    return int((end - started_at).total_seconds())
