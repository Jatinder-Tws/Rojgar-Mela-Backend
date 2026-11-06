"""Pure rules for the existing provider/seeker interview flow."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST_TZ = timezone(timedelta(hours=5, minutes=30))


def format_ist_clock(value: datetime) -> str:
    """Clock time in IST from the stored instant. Ignores a separate AM/PM flag."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    ist = value.astimezone(IST_TZ)
    hour = ist.hour % 12 or 12
    am_pm = "AM" if ist.hour < 12 else "PM"
    return f"{hour}:{ist.minute:02d} {am_pm} IST"


def auto_schedule_block_reason(
    interview_type: str | None,
    meeting_link: str | None,
    location: str | None,
    has_windows: bool,
) -> str | None:
    """Why auto-schedule must not create an interview. None means it may run."""
    if not has_windows:
        return "Add availability windows in interview settings before auto-schedule."
    kind = (interview_type or "video").strip().lower()
    if kind == "walk_in":
        if not (location or "").strip():
            return "Add a walk-in location in interview settings before enabling auto-schedule."
        return None
    link = (meeting_link or "").strip()
    if not link.startswith("http://") and not link.startswith("https://"):
        return "Add a video meeting link in interview settings before enabling auto-schedule."
    return None
