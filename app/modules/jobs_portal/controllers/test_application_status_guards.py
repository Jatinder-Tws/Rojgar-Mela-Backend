"""Regression: kanban 'move to Applied' must not break open interviews / closed apps."""

import pytest
from fastapi import HTTPException

from app.modules.jobs_portal.controllers.applications_controller import assert_can_move_to_applied
from app.modules.jobs_portal.models.application import ApplicationStatus


def test_applied_from_shortlisted_ok():
    assert_can_move_to_applied(ApplicationStatus.shortlisted, has_scheduled_interview=False)


def test_applied_blocked_when_interview_scheduled():
    with pytest.raises(HTTPException) as exc:
        assert_can_move_to_applied(ApplicationStatus.shortlisted, has_scheduled_interview=True)
    assert exc.value.status_code == 409


def test_applied_blocked_from_selected_or_interviewing():
    with pytest.raises(HTTPException) as exc:
        assert_can_move_to_applied(ApplicationStatus.selected, has_scheduled_interview=False)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc2:
        assert_can_move_to_applied(ApplicationStatus.interviewing, has_scheduled_interview=False)
    assert exc2.value.status_code == 400
