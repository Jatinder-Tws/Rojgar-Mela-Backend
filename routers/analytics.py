"""
Analytics router – aggregated stats for Seeker and Provider dashboards.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from database import get_db
from models.user import User, UserRole
from models.match import Match
from models.external_candidate_match import ExternalCandidateMatch
from models.job import JobPosting
from models.application import Application
from models.resume import Resume
from models.interview import Interview
from services.auth_service import require_verified

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/seeker")
async def seeker_stats(
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated analytics for a job seeker dashboard."""
    uid = user.id
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # Match score distribution
    matches_result = await db.execute(
        select(Match.score).where(Match.seeker_id == uid)
    )
    scores = [row[0] for row in matches_result.fetchall()]
    score_dist = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    for s in scores:
        if s < 25:
            score_dist["0-25"] += 1
        elif s < 50:
            score_dist["25-50"] += 1
        elif s < 75:
            score_dist["50-75"] += 1
        else:
            score_dist["75-100"] += 1

    # Applications by status
    apps_result = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.seeker_id == uid)
        .group_by(Application.status)
    )
    apps_by_status = {row[0]: row[1] for row in apps_result.fetchall()}

    # Matches over time (last 30 days)
    matches_time_result = await db.execute(
        select(
            func.date_trunc('day', Match.created_at).label('day'),
            func.count(Match.id)
        )
        .where(and_(Match.seeker_id == uid, Match.created_at >= thirty_days_ago))
        .group_by('day')
        .order_by('day')
    )
    matches_over_time = [
        {"date": row[0].isoformat() if row[0] else "", "count": row[1]}
        for row in matches_time_result.fetchall()
    ]

    # Top skills demanded from matched jobs
    matched_jobs_result = await db.execute(
        select(JobPosting.required_skills)
        .join(Match, Match.job_id == JobPosting.id)
        .where(Match.seeker_id == uid)
    )
    skill_counts: dict = {}
    for row in matched_jobs_result.fetchall():
        for skill in (row[0] or []):
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Profile completion (from portfolio)
    from models.portfolio import Portfolio
    from services.portfolio_service import calculate_completion
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == uid)
    )
    portfolio = portfolio_result.scalar_one_or_none()

    profile_completion = 0
    if portfolio:
        profile_completion, _, _ = calculate_completion(portfolio, user)

    # Upcoming interviews
    interviews_result = await db.execute(
        select(Interview)
        .where(and_(Interview.seeker_id == uid, Interview.scheduled_at >= now))
        .order_by(Interview.scheduled_at)
        .limit(5)
    )
    upcoming_interviews = []
    for i in interviews_result.scalars().all():
        sat = i.scheduled_at
        if sat:
            dt = sat.replace(tzinfo=timezone.utc) if sat.tzinfo is None else sat.astimezone(timezone.utc)
            sat_str = dt.isoformat().replace("+00:00", "Z") if dt.isoformat().endswith("+00:00") else dt.isoformat()
        else:
            sat_str = None
        upcoming_interviews.append({
            "id": str(i.id),
            "title": i.title,
            "scheduled_at": sat_str,
        })

    # Resume status
    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == uid).order_by(Resume.created_at.desc()).limit(1)
    )
    resume = resume_result.scalar_one_or_none()

    return {
        "total_matches": len(scores),
        "total_applications": sum(apps_by_status.values()),
        "shortlisted": apps_by_status.get("shortlisted", 0),
        "interviews_scheduled": len(upcoming_interviews),
        "profile_completion": profile_completion,
        "match_score_distribution": score_dist,
        "applications_by_status": apps_by_status,
        "matches_over_time": matches_over_time,
        "top_skills_demanded": [{"skill": s[0], "count": s[1]} for s in top_skills],
        "upcoming_interviews": upcoming_interviews,
        "has_resume": resume is not None,
        "resume_source": resume.source if resume else None,
    }


@router.get("/provider")
async def provider_stats(
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated analytics for a job provider dashboard."""
    uid = user.id
    now = datetime.utcnow()

    # Get provider's jobs
    jobs_result = await db.execute(
        select(JobPosting).where(JobPosting.provider_id == uid)
    )
    jobs = jobs_result.scalars().all()
    job_ids = [j.id for j in jobs]

    if not job_ids:
        return {
            "active_jobs": 0, "total_matches": 0, "total_external_matches": 0,
            "pending_external_count": 0,
            "total_applications": 0,
            "shortlisted": 0, "interviews_scheduled": 0,
            "applications_by_job": [], "match_score_distribution": {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0},
            "external_match_score_distribution": {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0},
            "hiring_funnel": {"matched": 0, "external_matched": 0, "applied": 0, "shortlisted": 0, "interviewed": 0},
            "top_candidate_skills": [], "jobs_performance": [],
        }

    active_jobs = sum(1 for j in jobs if j.is_active)

    # Match score distribution across all jobs
    matches_result = await db.execute(
        select(Match.score, Match.job_id).where(Match.job_id.in_(job_ids))
    )
    all_matches = matches_result.fetchall()
    scores = [row[0] for row in all_matches]
    score_dist = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    for s in scores:
        if s < 25: score_dist["0-25"] += 1
        elif s < 50: score_dist["25-50"] += 1
        elif s < 75: score_dist["50-75"] += 1
        else: score_dist["75-100"] += 1

    # ── External candidate AI matches ────────────────────────────────
    ext_matches_result = await db.execute(
        select(ExternalCandidateMatch.score, ExternalCandidateMatch.job_id)
        .where(ExternalCandidateMatch.job_id.in_(job_ids))
    )
    all_ext_matches = ext_matches_result.fetchall()
    ext_scores = [row[0] for row in all_ext_matches]
    ext_score_dist = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    for s in ext_scores:
        if s < 25:
            ext_score_dist["0-25"] += 1
        elif s < 50:
            ext_score_dist["25-50"] += 1
        elif s < 75:
            ext_score_dist["50-75"] += 1
        else:
            ext_score_dist["75-100"] += 1

    # Per-job external match counts
    ext_matches_per_job = {}
    for row in all_ext_matches:
        jid = str(row[1])
        ext_matches_per_job[jid] = ext_matches_per_job.get(jid, 0) + 1

    # ── Pending external candidates (not yet matched to any job) ──────
    pending_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM external_candidates "
            "WHERE is_matched = false AND status NOT IN ('rejected')"
        )
    )
    pending_external_count = pending_result.scalar() or 0

    # Applications by job
    apps_result = await db.execute(
        select(Application.job_id, Application.status, func.count(Application.id))
        .where(Application.job_id.in_(job_ids))
        .group_by(Application.job_id, Application.status)
    )
    apps_by_job_raw = apps_result.fetchall()
    
    # Build per-job app counts
    job_app_map: dict = {}
    total_apps = 0
    total_shortlisted = 0
    for row in apps_by_job_raw:
        jid, status, count = str(row[0]), row[1], row[2]
        if jid not in job_app_map:
            job_app_map[jid] = {"applied": 0, "shortlisted": 0, "rejected": 0, "interviewing": 0}
        job_app_map[jid][status] = job_app_map[jid].get(status, 0) + count
        total_apps += count
        if status == "shortlisted":
            total_shortlisted += count

    # Hiring funnel
    matches_per_job = {}
    for row in all_matches:
        jid = str(row[1])
        matches_per_job[jid] = matches_per_job.get(jid, 0) + 1

    interviews_result = await db.execute(
        select(func.count(Interview.id)).where(Interview.job_id.in_(job_ids))
    )
    total_interviews = interviews_result.scalar() or 0

    hiring_funnel = {
        "matched": len(scores),
        "external_matched": len(ext_scores),
        "applied": total_apps,
        "shortlisted": total_shortlisted,
        "interviewed": total_interviews,
    }

    # Top candidate skills from matched resumes
    matched_seeker_ids = await db.execute(
        select(Match.seeker_id).where(Match.job_id.in_(job_ids)).distinct()
    )
    seeker_ids = [str(row[0]) for row in matched_seeker_ids.fetchall()]
    
    skill_counts: dict = {}
    if seeker_ids:
        resumes_result = await db.execute(
            select(Resume.parsed_json).where(Resume.user_id.in_(seeker_ids))
        )
        for row in resumes_result.fetchall():
            pj = row[0] or {}
            for skill in (pj.get("skills", []) or []):
                s = skill if isinstance(skill, str) else skill.get("name", str(skill))
                skill_counts[s] = skill_counts.get(s, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Jobs performance
    jobs_performance = []
    for j in jobs:
        jid = str(j.id)
        apps = job_app_map.get(jid, {})
        jobs_performance.append({
            "id": jid,
            "title": j.title,
            "is_active": j.is_active,
            "matches_count": matches_per_job.get(jid, 0),
            "external_matches_count": ext_matches_per_job.get(jid, 0),
            "applications": sum(apps.values()),
            "shortlisted": apps.get("shortlisted", 0),
            "created_at": j.created_at.isoformat() if j.created_at else None,
        })

    # Applications by job (for chart)
    applications_by_job = [
        {
            "job_title": next((j.title for j in jobs if str(j.id) == jid), "Unknown"),
            **counts,
        }
        for jid, counts in job_app_map.items()
    ]

    return {
        "active_jobs": active_jobs,
        "total_matches": len(scores),
        "total_external_matches": len(ext_scores),
        "pending_external_count": pending_external_count,
        "total_applications": total_apps,
        "shortlisted": total_shortlisted,
        "interviews_scheduled": total_interviews,
        "match_score_distribution": score_dist,
        "external_match_score_distribution": ext_score_dist,
        "hiring_funnel": hiring_funnel,
        "applications_by_job": applications_by_job,
        "top_candidate_skills": [{"skill": s[0], "count": s[1]} for s in top_skills],
        "jobs_performance": jobs_performance,
    }
