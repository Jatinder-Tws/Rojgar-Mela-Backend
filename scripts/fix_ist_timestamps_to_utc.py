"""One-time, idempotent backfill to convert legacy naive-IST timestamps to UTC.

Older versions of training_portal stored `started_at`, `ended_at`, and
`marked_at` using `now_ist()` (naive IST wall-clock time) instead of UTC,
causing the frontend (`parseApiDate` + `formatIstDateTime`) to add +05:30 a
second time.

Usage:
    python scripts/fix_ist_timestamps_to_utc.py --dry-run
    python scripts/fix_ist_timestamps_to_utc.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.modules.training_portal.models.training_portal_attendance import (  # noqa: E402
    TrainingPortalAttendanceRecord,
)
from app.modules.training_portal.models.training_portal_class_session import (  # noqa: E402
    TrainingPortalClassSession,
)

IST_OFFSET = timedelta(hours=5, minutes=30)
DEFAULT_CUTOFF_UTC = datetime(2026, 11, 26, 11, 0, 0)


def _shift_iso_if_needed(raw: str | None) -> str | None:
    if not raw or not isinstance(raw, str):
        return raw
    text = raw.strip()
    if not text or text.endswith("Z") or "+" in text[10:]:
        return raw
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return raw
    return (dt - IST_OFFSET).isoformat()


async def run_backfill(apply: bool, cutoff_utc: datetime) -> None:
    async with AsyncSessionLocal() as db:
        # 1. Attendance records: marked_at was saved as now_ist() (~5h30m ahead of UTC created_at).
        records = (await db.execute(select(TrainingPortalAttendanceRecord))).scalars().all()
        rec_updates = 0
        for rec in records:
            if not rec.marked_at or not rec.created_at:
                continue
            if rec.marked_at - rec.created_at > timedelta(hours=4):
                rec_updates += 1
                if apply:
                    rec.marked_at = rec.marked_at - IST_OFFSET

        # 2. Class sessions: started_at, ended_at, and occurrence_reports entries created before cutoff.
        sessions = (await db.execute(select(TrainingPortalClassSession))).scalars().all()
        sess_updates = 0
        occ_updates = 0
        for sess in sessions:
            changed = False
            if sess.started_at and sess.started_at < cutoff_utc + IST_OFFSET:
                if (sess.updated_at and sess.updated_at < cutoff_utc) or (
                    sess.updated_at and sess.started_at - sess.updated_at > timedelta(hours=4)
                ):
                    if apply:
                        sess.started_at = sess.started_at - IST_OFFSET
                    changed = True

            if sess.ended_at and sess.ended_at < cutoff_utc + IST_OFFSET:
                if (sess.updated_at and sess.updated_at < cutoff_utc) or (
                    sess.updated_at and sess.ended_at - sess.updated_at > timedelta(hours=4)
                ):
                    if apply:
                        sess.ended_at = sess.ended_at - IST_OFFSET
                    changed = True

            reports = dict(sess.occurrence_reports or {}) if isinstance(sess.occurrence_reports, dict) else {}
            occ_changed = False
            for date_key, entry in list(reports.items()):
                if not isinstance(entry, dict) or entry.get("_utc_fixed"):
                    continue
                if date_key > cutoff_utc.date().isoformat():
                    continue
                new_entry = dict(entry)
                if new_entry.get("started_at"):
                    new_entry["started_at"] = _shift_iso_if_needed(new_entry["started_at"])
                    occ_changed = True
                if new_entry.get("ended_at"):
                    new_entry["ended_at"] = _shift_iso_if_needed(new_entry["ended_at"])
                    occ_changed = True
                if occ_changed:
                    new_entry["_utc_fixed"] = True
                    reports[date_key] = new_entry
                    occ_updates += 1

            if occ_changed:
                if apply:
                    sess.occurrence_reports = reports
                changed = True

            if changed:
                sess_updates += 1

        if apply:
            await db.commit()
            print(
                f"APPLIED: updated {rec_updates} attendance records, "
                f"{sess_updates} class sessions, {occ_updates} occurrence report entries."
            )
        else:
            print(
                f"DRY RUN: would update {rec_updates} attendance records, "
                f"{sess_updates} class sessions, {occ_updates} occurrence report entries. "
                "Re-run with --apply to commit."
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill legacy IST timestamps to UTC.")
    parser.add_argument("--apply", action="store_true", help="Commit changes to database.")
    parser.add_argument(
        "--before",
        default=DEFAULT_CUTOFF_UTC.isoformat(),
        help="UTC ISO cutoff for legacy session rows (default: 2026-11-26T11:00:00).",
    )
    args = parser.parse_args()
    cutoff = datetime.fromisoformat(args.before)
    asyncio.run(run_backfill(apply=args.apply, cutoff_utc=cutoff))


if __name__ == "__main__":
    main()
