"""Public marketing stats aggregated from live platform data."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import redis.asyncio as aioredis
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.jobs_portal.models.application import Application, ApplicationStatus
from app.modules.jobs_portal.models.external_candidate import ExternalCandidate
from app.modules.jobs_portal.models.job import JobPosting
from app.modules.jobs_portal.models.match import Match
from app.modules.jobs_portal.services.public_jobs_service import _extract_city_label
from app.modules.training_portal.models.training_portal_course import TrainingPortalCourse
from app.modules.training_portal.models.training_portal_enrollment import TrainingPortalEnrollment
from app.modules.training_portal.models.training_portal_free_course import TrainingPortalFreeCourse
from app.shared.models.user import User, UserRole

logger = logging.getLogger(__name__)

CACHE_KEY = "platform:public_stats:v3"
CACHE_TTL_SECONDS = 300
_NON_CITIES = {
    "remote",
    "wfh",
    "work from home",
    "work from office",
    "hybrid",
    "india",
    "pan india",
    "anywhere",
    "n/a",
    "na",
    "multiple",
    "various",
    "nationwide",
}


async def _redis() -> Optional[aioredis.Redis]:
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2.0)
        await client.ping()
        return client
    except Exception as exc:
        logger.warning("[PlatformStats] Redis unavailable: %s", exc)
        return None


def _is_city(label: Optional[str]) -> bool:
    if not label:
        return False
    key = label.strip().lower()
    return bool(key) and key not in _NON_CITIES and len(key) > 1


def _salary_to_lpa(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))]
    if not nums:
        return None
    mid = (nums[0] + nums[1]) / 2 if len(nums) >= 2 else nums[0]
    lower = text.lower()
    if "lpa" in lower or "lakh" in lower:
        return round(mid / 100000, 2) if mid >= 1000 else round(mid, 2)
    if mid >= 100000:
        return round(mid / 100000, 2)
    if mid > 100:
        return None
    return round(mid, 2)


async def get_public_platform_stats(db: AsyncSession) -> dict[str, Any]:
    redis_client = await _redis()
    if redis_client:
        try:
            cached = await redis_client.get(CACHE_KEY)
            if cached:
                await redis_client.close()
                return json.loads(cached)
        except Exception as exc:
            logger.warning("[PlatformStats] Redis get failed: %s", exc)

    stats = await _compute_stats(db)

    if redis_client:
        try:
            await redis_client.setex(CACHE_KEY, CACHE_TTL_SECONDS, json.dumps(stats))
            await redis_client.close()
        except Exception as exc:
            logger.warning("[PlatformStats] Redis set failed: %s", exc)

    return stats


async def _count(db: AsyncSession, query) -> int:
    return int(await db.scalar(query) or 0)


async def _compute_stats(db: AsyncSession) -> dict[str, Any]:
    seekers = await _count(
        db,
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False)),
    )
    recruiters = await _count(
        db,
        select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False)),
    )
    external = await _count(
        db,
        select(func.count(distinct(func.lower(ExternalCandidate.email)))).where(
            ExternalCandidate.email.isnot(None),
            func.trim(ExternalCandidate.email) != "",
        ),
    )
    overlap = await _count(
        db,
        select(func.count(distinct(func.lower(User.email)))).where(
            User.role == UserRole.seeker,
            User.email.isnot(None),
            func.lower(User.email).in_(
                select(func.lower(ExternalCandidate.email)).where(
                    ExternalCandidate.email.isnot(None),
                    func.trim(ExternalCandidate.email) != "",
                )
            ),
        ),
    )
    total_seekers = max(0, seekers + external - overlap)

    active_jobs = await _count(
        db,
        select(func.count(JobPosting.id)).where(JobPosting.is_active.is_(True)),
    )
    industries = len(
        [
            "sales",
            "healthcare",
            "it",
            "retail",
            "delivery",
            "bpo",
            "finance",
            "hr",
            "marketing",
            "manufacturing",
            "hospitality",
            "education",
            "construction",
            "data_science",
            "customer_support",
            "admin",
        ]
    )

    # Hiring partners = employer/recruiter accounts (same pool shown as "Recruiters")
    hiring_partners = recruiters

    selected_seekers = await _count(
        db,
        select(func.count(distinct(Application.seeker_id))).where(
            Application.status == ApplicationStatus.selected,
            Application.seeker_id.isnot(None),
        ),
    )
    selected_guests = await _count(
        db,
        select(func.count(distinct(func.lower(Application.candidate_email)))).where(
            Application.status == ApplicationStatus.selected,
            Application.seeker_id.is_(None),
            Application.candidate_email.isnot(None),
            func.trim(Application.candidate_email) != "",
        ),
    )
    students_placed = selected_seekers + selected_guests

    selected_n = await _count(
        db,
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.selected),
    )
    rejected_n = await _count(
        db,
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.rejected),
    )
    decided = selected_n + rejected_n
    success_rate = round((selected_n / decided) * 100, 1) if decided else None

    avg_placement_days = await db.scalar(
        select(
            func.avg(func.extract("epoch", Application.updated_at - Application.applied_at) / 86400.0)
        ).where(
            Application.status == ApplicationStatus.selected,
            Application.applied_at.isnot(None),
            Application.updated_at.isnot(None),
        )
    )
    avg_shortlist_hours = await db.scalar(
        select(
            func.avg(func.extract("epoch", Application.updated_at - Application.applied_at) / 3600.0)
        ).where(
            Application.status.in_(
                (ApplicationStatus.shortlisted, ApplicationStatus.interviewing, ApplicationStatus.selected)
            ),
            Application.applied_at.isnot(None),
            Application.updated_at.isnot(None),
        )
    )
    avg_match_score = await db.scalar(select(func.avg(Match.score)))

    learners_trained = await _count(
        db,
        select(func.count(distinct(func.lower(TrainingPortalEnrollment.candidate_email)))).where(
            TrainingPortalEnrollment.status.in_(("active", "completed")),
            TrainingPortalEnrollment.candidate_email.isnot(None),
            func.trim(TrainingPortalEnrollment.candidate_email) != "",
        ),
    )
    paid_courses = await _count(
        db,
        select(func.count(TrainingPortalCourse.id)).where(TrainingPortalCourse.status == "published"),
    )
    free_courses = await _count(
        db,
        select(func.count(TrainingPortalFreeCourse.id)).where(TrainingPortalFreeCourse.status == "published"),
    )
    certificates_issued = await _count(
        db,
        select(func.count(TrainingPortalEnrollment.id)).where(
            TrainingPortalEnrollment.is_certificate_issued.is_(True)
        ),
    )

    salary_rows = (
        await db.execute(
            select(JobPosting.salary_range)
            .join(Application, Application.job_id == JobPosting.id)
            .where(
                Application.status == ApplicationStatus.selected,
                JobPosting.salary_range.isnot(None),
                func.trim(JobPosting.salary_range) != "",
            )
        )
    ).all()
    lpas = [v for (raw,) in salary_rows if (v := _salary_to_lpa(raw)) is not None]
    avg_alumni_lpa = round(sum(lpas) / len(lpas), 1) if lpas else None

    cities: set[str] = set()
    # Cities must match Find Jobs location chips — active job postings only
    job_locs = (
        await db.execute(
            select(JobPosting.location).where(
                JobPosting.is_active.is_(True),
                JobPosting.location.isnot(None),
                func.trim(JobPosting.location) != "",
            ).distinct()
        )
    ).all()
    for (loc,) in job_locs:
        city = _extract_city_label(loc or "")
        if _is_city(city):
            cities.add(city.lower())

    return {
        "seekers": total_seekers,
        "recruiters": recruiters,
        "cities": len(cities),
        "active_jobs": active_jobs,
        "industries": industries,
        "hiring_partners": hiring_partners,
        "students_placed": students_placed,
        "success_rate": success_rate,
        "avg_placement_days": round(float(avg_placement_days), 1) if avg_placement_days else None,
        "avg_shortlist_hours": round(float(avg_shortlist_hours), 1) if avg_shortlist_hours else None,
        "avg_match_score": round(float(avg_match_score), 1) if avg_match_score else None,
        "learners_trained": learners_trained,
        "courses_published": paid_courses + free_courses,
        "certificates_issued": certificates_issued,
        "avg_alumni_lpa": avg_alumni_lpa,
    }
