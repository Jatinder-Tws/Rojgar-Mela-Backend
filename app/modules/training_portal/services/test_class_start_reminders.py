from datetime import date, datetime
from types import SimpleNamespace

from app.modules.training_portal.services.training_portal_class_live import (
    pending_reminder_tier,
    sync_start_reminder_day,
)


def _session(**overrides):
    base = dict(
        postponed=False,
        teacher_unavailable=False,
        schedule_type="one_time",
        days=[],
        date="2026-11-04",
        start_time="10:00 AM",
        end_time="12:00 PM",
        live_status="scheduled",
        live_occurrence_date=None,
        reminder_sent=False,
        reminder_15_sent=False,
        start_reminder_for_date=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_sync_start_reminder_day_resets_only_on_new_day():
    session = _session(reminder_sent=True, reminder_15_sent=True, start_reminder_for_date="2026-11-03")
    sync_start_reminder_day(session, date(2026, 11, 4))
    assert session.reminder_sent is False
    assert session.reminder_15_sent is False
    assert session.start_reminder_for_date == "2026-11-04"

    session.reminder_sent = True
    session.reminder_15_sent = True
    sync_start_reminder_day(session, date(2026, 11, 4))
    assert session.reminder_sent is True
    assert session.reminder_15_sent is True


def test_30_and_15_each_once_same_day():
    target = date(2026, 11, 4)
    session = _session()

    # 25 minutes before → 30-min tier
    now = datetime(2026, 11, 4, 9, 35, 0)
    assert pending_reminder_tier(session, now, target) == 30
    session.reminder_sent = True

    assert pending_reminder_tier(session, now, target) is None

    # 12 minutes before → 15-min tier once
    now15 = datetime(2026, 11, 4, 9, 48, 0)
    assert pending_reminder_tier(session, now15, target) == 15
    session.reminder_15_sent = True
    assert pending_reminder_tier(session, now15, target) is None

    # Still in window — no repeats
    assert pending_reminder_tier(session, datetime(2026, 11, 4, 9, 50, 0), target) is None


def test_no_reminder_when_session_not_scheduled_today():
    session = _session(date="2026-11-05")
    now = datetime(2026, 11, 4, 9, 40, 0)
    assert pending_reminder_tier(session, now, date(2026, 11, 4)) is None


def test_recurring_resets_next_day():
    # 2026-11-04 is Wednesday; next occurrence Thursday 2026-11-05.
    target = date(2026, 11, 5)
    session = _session(
        schedule_type="recurring",
        days=["Thu"],
        date="2026-11-01",
        reminder_sent=True,
        reminder_15_sent=True,
        start_reminder_for_date="2026-11-04",
        start_time="10:00 AM",
    )
    now = datetime(2026, 11, 5, 9, 35, 0)
    assert pending_reminder_tier(session, now, target) == 30
    assert session.start_reminder_for_date == "2026-11-05"
    assert session.reminder_sent is False
