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


def snapshot_session_fields(session) -> dict[str, Any]:
    return {
        "session_report": getattr(session, "session_report", None),
        "covered_topic_ids": list(getattr(session, "covered_topic_ids", None) or []),
        "attachment_url": getattr(session, "attachment_url", None),
        "attachment_filename": getattr(session, "attachment_filename", None),
        "late_start_reason": getattr(session, "late_start_reason", None),
        "early_end_reason": getattr(session, "early_end_reason", None),
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
    if date_key and date_key == live:
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
