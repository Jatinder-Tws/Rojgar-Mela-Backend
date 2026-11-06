from datetime import datetime, timezone

from app.modules.jobs_portal.services.interview_flow import (
    auto_schedule_block_reason,
    format_ist_clock,
)


def test_clock_uses_ist_instant_not_a_separate_period():
    # 10:00 UTC is 3:30 PM IST. A stored AM flag must not rewrite it to morning.
    instant = datetime(2026, 11, 6, 10, 0, tzinfo=timezone.utc)
    assert format_ist_clock(instant) == "3:30 PM IST"


def test_auto_schedule_requires_windows_and_a_real_meeting_place():
    assert auto_schedule_block_reason("video", "https://meet.google.com/abc", None, False)
    assert auto_schedule_block_reason("video", "", None, True)
    assert auto_schedule_block_reason("video", "meet.google.com/abc", None, True)
    assert auto_schedule_block_reason("walk_in", None, "  ", True)
    assert auto_schedule_block_reason("video", "https://meet.google.com/abc", None, True) is None
    assert auto_schedule_block_reason("walk_in", None, "Sector 17, Chandigarh", True) is None
