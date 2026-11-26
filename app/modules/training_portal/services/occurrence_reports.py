"""Per-occurrence class notes / MOM and topic coverage helpers.

Recurring class sessions reuse one row across dates. Live fields on the session
(session_report, covered_topic_ids, attachments) only reflect the latest
occurrence. Historical values are stored in occurrence_reports keyed by date.
"""

from __future__ import annotations

from typing import Any, Optional


def _reports_map(session) -> dict[str, Any]:
    raw = getattr(session, "occurrence_reports", None) or {}
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def _iso_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def snapshot_session_fields(session) -> dict[str, Any]:
    return {
        "session_report": getattr(session, "session_report", None),
        "covered_topic_ids": list(getattr(session, "covered_topic_ids", None) or []),
        "attachment_url": getattr(session, "attachment_url", None),
        "attachment_filename": getattr(session, "attachment_filename", None),
        "late_start_reason": getattr(session, "late_start_reason", None),
        "early_end_reason": getattr(session, "early_end_reason", None),
        "started_at": _iso_or_none(getattr(session, "started_at", None)),
        "ended_at": _iso_or_none(getattr(session, "ended_at", None)),
    }


def archive_current_occurrence(session, occurrence_date: Optional[str]) -> None:
    """Persist current live fields under occurrence_date before they are cleared."""
    date_key = (occurrence_date or "").strip()
    if not date_key:
        return
    reports = _reports_map(session)
    existing = dict(reports.get(date_key) or {}) if isinstance(reports.get(date_key), dict) else {}
    snap = snapshot_session_fields(session)
    # Keep any existing note if the live field was already cleared.
    if not (snap.get("session_report") or "").strip() and (existing.get("session_report") or "").strip():
        snap["session_report"] = existing.get("session_report")
    if not snap.get("covered_topic_ids") and existing.get("covered_topic_ids"):
        snap["covered_topic_ids"] = list(existing.get("covered_topic_ids") or [])
    if not snap.get("attachment_url") and existing.get("attachment_url"):
        snap["attachment_url"] = existing.get("attachment_url")
        snap["attachment_filename"] = existing.get("attachment_filename")
    reports[date_key] = {**existing, **snap}
    session.occurrence_reports = reports


def upsert_occurrence_fields(session, occurrence_date: str, **fields: Any) -> dict[str, Any]:
    date_key = (occurrence_date or "").strip()
    if not date_key:
        raise ValueError("occurrence_date is required")
    reports = _reports_map(session)
    entry = dict(reports.get(date_key) or {}) if isinstance(reports.get(date_key), dict) else {}
    for key, value in fields.items():
        entry[key] = value
    reports[date_key] = entry
    session.occurrence_reports = reports
    return entry


def get_occurrence_fields(session, occurrence_date: Optional[str]) -> dict[str, Any]:
    date_key = (occurrence_date or "").strip()
    reports = _reports_map(session)
    entry: dict[str, Any] = {}
    if date_key and isinstance(reports.get(date_key), dict):
        entry = dict(reports[date_key])

    live = (getattr(session, "live_occurrence_date", None) or "").strip()
    if (date_key and date_key == live) or not date_key:
        # Live columns are source of truth for the active/latest occurrence.
        live_snap = snapshot_session_fields(session)
        for key, value in live_snap.items():
            if key == "covered_topic_ids":
                if value or key not in entry:
                    entry[key] = value
            elif value is not None and value != "":
                entry[key] = value
            elif key not in entry:
                entry[key] = value

    # Fallback to session live fields only when no specific date was requested
    # or when the requested date matches the session's active/non-recurring date.
    # Otherwise a recurring session's previous occurrence notes/late_start_reason
    # would leak onto a new unstarted day and falsely mark it completed.
    is_recurring = getattr(session, "schedule_type", None) == "recurring"
    allow_live_fallback = (not date_key) or (date_key == live) or (not is_recurring and not live)
    if allow_live_fallback:
        if not entry.get("session_report") and getattr(session, "session_report", None):
            entry["session_report"] = session.session_report
        if not entry.get("covered_topic_ids") and getattr(session, "covered_topic_ids", None):
            entry["covered_topic_ids"] = list(session.covered_topic_ids or [])
        if not entry.get("attachment_url") and getattr(session, "attachment_url", None):
            entry["attachment_url"] = session.attachment_url
            entry["attachment_filename"] = getattr(session, "attachment_filename", None)
        if not entry.get("late_start_reason") and getattr(session, "late_start_reason", None):
            entry["late_start_reason"] = session.late_start_reason
        if not entry.get("early_end_reason") and getattr(session, "early_end_reason", None):
            entry["early_end_reason"] = session.early_end_reason
        if not entry.get("started_at") and getattr(session, "started_at", None):
            entry["started_at"] = _iso_or_none(session.started_at)
        if not entry.get("ended_at") and getattr(session, "ended_at", None):
            entry["ended_at"] = _iso_or_none(session.ended_at)

    return entry


def resolve_session_report(session, occurrence_date: Optional[str]) -> Optional[str]:
    entry = get_occurrence_fields(session, occurrence_date)
    report = entry.get("session_report")
    if isinstance(report, str) and report.strip():
        return report
    if report is None or report == "":
        return None
    return str(report) if report else None


def resolve_covered_topic_ids(session, occurrence_date: Optional[str]) -> list[str]:
    entry = get_occurrence_fields(session, occurrence_date)
    topics = entry.get("covered_topic_ids")
    if isinstance(topics, list):
        return [str(t) for t in topics]
    return []
