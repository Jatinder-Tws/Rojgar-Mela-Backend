from app.modules.jobs_portal.services.interview_scheduling_dbservice import format_outcome_notes


def test_format_outcome_notes_reason_and_text():
    assert (
        format_outcome_notes("candidate_no_show", "  waited 15 min  ")
        == "Candidate did not join. waited 15 min"
    )


def test_format_outcome_notes_reason_only():
    assert format_outcome_notes("skills_gap", None) == "Skills gap"
    assert format_outcome_notes("skills_gap", "   ") == "Skills gap"


def test_format_outcome_notes_empty():
    assert format_outcome_notes(None, None) is None
    assert format_outcome_notes(None, "  ") is None
