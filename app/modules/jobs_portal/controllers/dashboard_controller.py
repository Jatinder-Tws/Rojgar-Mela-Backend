"""Bundled dashboard payloads to reduce round-trips for provider and seeker UIs."""
import asyncio
from datetime import datetime, timezone
from typing import Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.user import User
from app.modules.jobs_portal.controllers.jobs_controller import list_jobs
from app.modules.jobs_portal.controllers.matches_controller import get_matched_candidates, get_matched_jobs
from app.modules.jobs_portal.controllers.applications_controller import get_all_applicants, get_my_applications
from app.modules.jobs_portal.controllers.analytics_controller import provider_stats, seeker_stats
from app.shared.controllers.notifications_controller import get_notifications
from app.modules.jobs_portal.controllers.assessment_controller import get_my_assessment
from app.modules.jobs_portal.services.interview_scheduling_dbservice import get_user_interviews
from app.modules.jobs_portal.services.job_fair_db import list_job_fairs_db
from app.modules.jobs_portal.services.roadmap_service import RoadmapService


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


async def _safe_eval(coro, fallback):
    try:
        res = await coro
        return _serialize(res)
    except Exception:
        return fallback


async def provider_dashboard(user: User, db: AsyncSession) -> dict:
    jobs = await _safe_eval(list_jobs(user, db), [])
    analytics = await _safe_eval(provider_stats(user, db), None)
    candidates = await _safe_eval(get_matched_candidates(None, True, user, db), [])
    applications = await _safe_eval(get_all_applicants(user, db), [])
    interviews = await _safe_eval(get_user_interviews(db, user), [])
    try:
        job_fairs = await _upcoming_job_fairs(db)
    except Exception:
        job_fairs = []

    return {
        "jobs": jobs,
        "analytics": analytics,
        "candidates": candidates,
        "applications": applications,
        "interviews": interviews,
        "upcoming_job_fairs": job_fairs,
    }


async def seeker_dashboard(user: User, db: AsyncSession) -> dict:
    roadmap_service = RoadmapService()
    jobs = await _safe_eval(get_matched_jobs(user, db), [])
    applications = await _safe_eval(get_my_applications(user, db), [])
    analytics = await _safe_eval(seeker_stats(user, db), None)
    notifications = await _safe_eval(get_notifications(user, db), [])
    assessment = await _safe_eval(get_my_assessment(user, db), None)
    roadmaps = await _safe_eval(roadmap_service.get_user_roadmaps(str(user.id), db, limit=20, offset=0), [])
    interviews = await _safe_eval(get_user_interviews(db, user), [])

    return {
        "jobs": jobs,
        "applications": applications,
        "analytics": analytics,
        "notifications": notifications,
        "assessment": assessment,
        "roadmaps": roadmaps,
        "interviews": interviews,
    }
