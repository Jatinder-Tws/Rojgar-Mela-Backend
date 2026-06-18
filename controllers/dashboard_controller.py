"""Bundled dashboard payloads to reduce round-trips for provider and seeker UIs."""
import asyncio
from datetime import datetime, timezone
from typing import Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from controllers.jobs_controller import list_jobs
from controllers.matches_controller import get_matched_candidates, get_matched_jobs
from controllers.applications_controller import get_all_applicants, get_my_applications
from controllers.analytics_controller import provider_stats, seeker_stats
from controllers.notifications_controller import get_notifications
from controllers.assessment_controller import get_my_assessment
from services.interview_scheduling_dbservice import get_user_interviews
from services.job_fair_db import list_job_fairs_db
from services.roadmap_service import RoadmapService


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return value


async def _upcoming_job_fairs(db: AsyncSession, limit: int = 3) -> List[dict]:
    items, _ = await list_job_fairs_db(
        db,
        search=None,
        sort_by="date_asc",
        page=1,
        page_size=30,
    )
    now = datetime.now(timezone.utc)
    upcoming = []
    for fair in items:
        if not getattr(fair, "is_active", True):
            continue
        fair_date = getattr(fair, "date", None)
        if fair_date is None:
            continue
        if fair_date.tzinfo is None:
            fair_date = fair_date.replace(tzinfo=timezone.utc)
        if fair_date <= now:
            continue
        upcoming.append(_serialize(fair))
    upcoming.sort(key=lambda f: f.get("date") or "")
    return upcoming[:limit]


async def provider_dashboard(user: User, db: AsyncSession) -> dict:
    results = await asyncio.gather(
        list_jobs(user, db),
        provider_stats(user, db),
        get_matched_candidates(None, True, user, db),
        get_all_applicants(user, db),
        get_user_interviews(db, user),
        _upcoming_job_fairs(db),
        return_exceptions=True,
    )

    jobs, analytics, candidates, applications, interviews, job_fairs = results

    return {
        "jobs": _serialize(jobs) if not isinstance(jobs, Exception) else [],
        "analytics": _serialize(analytics) if not isinstance(analytics, Exception) else None,
        "candidates": _serialize(candidates) if not isinstance(candidates, Exception) else [],
        "applications": _serialize(applications) if not isinstance(applications, Exception) else [],
        "interviews": _serialize(interviews) if not isinstance(interviews, Exception) else [],
        "upcoming_job_fairs": job_fairs if not isinstance(job_fairs, Exception) else [],
    }


async def seeker_dashboard(user: User, db: AsyncSession) -> dict:
    roadmap_service = RoadmapService()
    results = await asyncio.gather(
        get_matched_jobs(user, db),
        get_my_applications(user, db),
        seeker_stats(user, db),
        get_notifications(user, db),
        get_my_assessment(user, db),
        roadmap_service.get_user_roadmaps(str(user.id), db, limit=20, offset=0),
        get_user_interviews(db, user),
        return_exceptions=True,
    )

    jobs, applications, analytics, notifications, assessment, roadmaps, interviews = results

    return {
        "jobs": _serialize(jobs) if not isinstance(jobs, Exception) else [],
        "applications": _serialize(applications) if not isinstance(applications, Exception) else [],
        "analytics": _serialize(analytics) if not isinstance(analytics, Exception) else None,
        "notifications": _serialize(notifications) if not isinstance(notifications, Exception) else [],
        "assessment": _serialize(assessment) if not isinstance(assessment, Exception) else None,
        "roadmaps": _serialize(roadmaps) if not isinstance(roadmaps, Exception) else [],
        "interviews": _serialize(interviews) if not isinstance(interviews, Exception) else [],
    }
