"""Read helpers for assessment results (kept free of router/schema imports)."""

from sqlalchemy import select

from app.modules.jobs_portal.models.assessment import AssessmentResult


def latest_assessment_for_user_query(user_id: str):
    """Prefer the newest result when a user has retaken the assessment.

    Using scalar_one_or_none() on all rows raises MultipleResultsFound and the
    seeker dashboard then silently drops assessment to null.
    """
    return (
        select(AssessmentResult)
        .where(AssessmentResult.user_id == user_id)
        .order_by(AssessmentResult.created_at.desc())
        .limit(1)
    )
