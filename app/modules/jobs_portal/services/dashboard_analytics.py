"""Comprehensive dashboard analytics for super admin."""
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.jobs_portal.models.application import Application, ApplicationStatus
from app.modules.jobs_portal.models.ai_interview import AIInterviewSession
from app.modules.jobs_portal.models.interview import Interview
from app.modules.jobs_portal.models.job import JobPosting
from app.modules.jobs_portal.models.match import Match
from app.modules.jobs_portal.models.portfolio import Portfolio
from app.shared.models.user import User, UserRole
from app.modules.jobs_portal.services.portfolio_service import calculate_completion


def _pct_change(today: int, yesterday: int) -> float:
    if yesterday == 0:
        return 100.0 if today > 0 else 0.0
    return round(((today - yesterday) / yesterday) * 100, 1)


def _funnel_pct(count: int, base: int) -> float:
    if base <= 0:
        return 0.0
    return round(min((count / base) * 100, 100.0), 1)


def _day_bounds(target: datetime):
    start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    prev_start = start - timedelta(days=1)
    return start, end, prev_start, start


def _resolve_period_bounds(
    target_date: Optional[datetime],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    if start_date and end_date:
        period_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = end_date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        period_days = max((period_end - period_start).days, 1)
        prev_end = period_start
        prev_start = prev_end - timedelta(days=period_days)
        return period_start, period_end, prev_start, prev_end
    now = target_date or datetime.utcnow()
    return _day_bounds(now)


def _kpi_labels(period_start: datetime, period_end: datetime) -> dict[str, str]:
    """Human-readable KPI labels based on selected reporting period."""
    period_days = max((period_end - period_start).days, 1)
    is_single_day = period_days == 1
    is_calendar_month = (
        period_start.day == 1
        and period_start.month == (period_end - timedelta(days=1)).month
        and period_start.year == (period_end - timedelta(days=1)).year
    )
    if is_single_day:
        suffix = "Today"
    elif is_calendar_month:
        suffix = "This Month"
    else:
        suffix = "In Period"

    def _period_label(base: str) -> str:
        if is_single_day:
            return f"{base} Today"
        if suffix == "In Period":
            return base
        return f"{base} {suffix}"

    return {
        "new_registrations": _period_label("New Registrations"),
        "active_jobs": "Active Jobs",
        "applications": _period_label("Applications"),
        "interviews": _period_label("Interviews"),
        "new_matches": _period_label("New Matches"),
        "selections": _period_label("Selections"),
        "companies_active": "Companies Active",
    }


def _calculate_completion_raw(
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    is_assessment_done: bool,
    has_portfolio: bool,
    headline: str | None,
    bio: str | None,
    city: str | None,
    state: str | None,
    linkedin_url: str | None,
    github_url: str | None,
    website_url: str | None,
    skills: list | str | None,
    work_experiences: list | str | None,
    education: list | str | None,
    certifications: list | str | None,
    languages: list | str | None,
    projects: list | str | None,
    intro_video_path: str | None,
    intro_audio_path: str | None,
) -> int:
    from app.modules.jobs_portal.services.portfolio_service import (
        normalize_skills,
        normalize_work_experiences,
        normalize_education,
        normalize_certifications,
        normalize_languages,
        normalize_projects
    )

    if not has_portfolio:
        sections = {
            "Personal Details": bool(first_name and last_name and email),
            "Headline": False,
            "Bio / About Me": False,
            "Location": False,
            "Skills": False,
            "Work Experience": False,
            "Education": False,
            "Social Links": False,
            "Certifications": False,
            "Languages": False,
            "Projects": False,
            "Intro Video / Audio": False,
            "AI Assessment": bool(is_assessment_done),
        }
    else:
        norm_skills = normalize_skills(skills)
        norm_work = normalize_work_experiences(work_experiences)
        norm_edu = normalize_education(education)
        norm_cert = normalize_certifications(certifications)
        norm_lang = normalize_languages(languages)
        norm_proj = normalize_projects(projects)

        sections = {
            "Personal Details": bool(first_name and last_name and email),
            "Headline": bool(headline),
            "Bio / About Me": bool(bio),
            "Location": bool(city or state),
            "Skills": bool(norm_skills),
            "Work Experience": bool(norm_work),
            "Education": bool(norm_edu),
            "Social Links": bool(linkedin_url or github_url or website_url),
            "Certifications": bool(norm_cert),
            "Languages": bool(norm_lang),
            "Projects": bool(norm_proj),
            "Intro Video / Audio": bool(intro_video_path or intro_audio_path),
            "AI Assessment": bool(is_assessment_done),
        }
    filled = sum(1 for v in sections.values() if v)
    return int((filled / len(sections)) * 100) if sections else 0


async def get_dashboard_analytics(
    db: AsyncSession,
    target_date: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    import asyncio
    now = end_date or target_date or datetime.utcnow()
    day_start, day_end, yesterday_start, yesterday_end = _resolve_period_bounds(
        target_date, start_date, end_date
    )

    Seeker = aliased(User)
    Provider = aliased(User)

    # ── 1. Define Consolidated Queries ─────────────────────────────────────────

    # Query 1: Totals & period KPIs
    totals_query = select(
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False)).scalar_subquery().label("total_seekers"),
        select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False)).scalar_subquery().label("total_providers"),
        select(func.count(JobPosting.id)).scalar_subquery().label("total_jobs"),
        select(func.count(JobPosting.id)).where(JobPosting.is_active.is_(True)).scalar_subquery().label("active_jobs"),
        select(func.count(Application.id)).scalar_subquery().label("total_applications"),
        select(func.count(Match.id)).scalar_subquery().label("total_matches"),
        select(func.count(User.id)).where(User.is_super_admin.is_(False), User.created_at >= day_start, User.created_at < day_end).scalar_subquery().label("new_regs_today"),
        select(func.count(User.id)).where(User.is_super_admin.is_(False), User.created_at >= yesterday_start, User.created_at < yesterday_end).scalar_subquery().label("new_regs_yesterday"),
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False), User.created_at >= day_start, User.created_at < day_end).scalar_subquery().label("new_seekers_period"),
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False), User.created_at >= yesterday_start, User.created_at < yesterday_end).scalar_subquery().label("new_seekers_prev"),
        select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False), User.created_at >= day_start, User.created_at < day_end).scalar_subquery().label("new_providers_period"),
        select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False), User.created_at >= yesterday_start, User.created_at < yesterday_end).scalar_subquery().label("new_providers_prev"),
        select(func.count(Application.id)).where(Application.applied_at >= day_start, Application.applied_at < day_end).scalar_subquery().label("apps_today"),
        select(func.count(Application.id)).where(Application.applied_at >= yesterday_start, Application.applied_at < yesterday_end).scalar_subquery().label("apps_yesterday"),
        select(func.count(Interview.id)).where(Interview.scheduled_at >= day_start, Interview.scheduled_at < day_end).scalar_subquery().label("interviews_today"),
        select(func.count(Interview.id)).where(Interview.scheduled_at >= yesterday_start, Interview.scheduled_at < yesterday_end).scalar_subquery().label("interviews_yesterday"),
        select(func.count(Match.id)).where(Match.created_at >= day_start, Match.created_at < day_end).scalar_subquery().label("matches_today"),
        select(func.count(Match.id)).where(Match.created_at >= yesterday_start, Match.created_at < yesterday_end).scalar_subquery().label("matches_yesterday"),
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.shortlisted, Application.updated_at >= day_start, Application.updated_at < day_end).scalar_subquery().label("selections_today"),
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.shortlisted, Application.updated_at >= yesterday_start, Application.updated_at < yesterday_end).scalar_subquery().label("selections_yesterday"),
        select(func.count(func.distinct(JobPosting.provider_id))).where(JobPosting.is_active.is_(True)).scalar_subquery().label("companies_active"),
        select(func.count(func.distinct(JobPosting.provider_id))).where(JobPosting.is_active.is_(True), JobPosting.updated_at < day_end).scalar_subquery().label("companies_active_yesterday"),
        select(func.count(JobPosting.id)).where(JobPosting.is_active.is_(True), JobPosting.created_at < day_end).scalar_subquery().label("active_jobs_yesterday"),
    )

    # Query 2: Summary Columns & Funnel Stage Counts (21 counts in a single query)
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    summary_counts_query = select(
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False), User.onboarding_complete.is_(True)).scalar_subquery().label("active_seekers"),
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False), User.created_at >= thirty_days_ago).scalar_subquery().label("seekers_30d"),
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False), User.created_at >= sixty_days_ago, User.created_at < thirty_days_ago).scalar_subquery().label("seekers_prev_30d"),
        select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False), User.created_at >= thirty_days_ago).scalar_subquery().label("providers_30d"),
        select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False), User.created_at >= sixty_days_ago, User.created_at < thirty_days_ago).scalar_subquery().label("providers_prev_30d"),
        select(func.count(func.distinct(JobPosting.provider_id))).select_from(Application).join(JobPosting, Application.job_id == JobPosting.id).scalar_subquery().label("hiring_companies"),
        select(func.count(func.distinct(JobPosting.provider_id))).select_from(Application).join(JobPosting, Application.job_id == JobPosting.id).where(Application.applied_at < thirty_days_ago).scalar_subquery().label("hiring_companies_prev"),
        select(func.count(JobPosting.id)).where(JobPosting.created_at >= thirty_days_ago).scalar_subquery().label("jobs_30d"),
        select(func.count(JobPosting.id)).where(JobPosting.created_at >= sixty_days_ago, JobPosting.created_at < thirty_days_ago).scalar_subquery().label("jobs_prev_30d"),
        select(func.count(JobPosting.id)).where(JobPosting.ai_interview_enabled.is_(True)).scalar_subquery().label("featured_jobs"),
        select(func.count(JobPosting.id)).where(JobPosting.ai_interview_enabled.is_(True), JobPosting.created_at < thirty_days_ago).scalar_subquery().label("featured_prev"),
        select(func.count(JobPosting.id)).where(JobPosting.is_active.is_(False), JobPosting.updated_at < thirty_days_ago).scalar_subquery().label("inactive_prev"),
        select(func.count(Application.id)).where(Application.applied_at >= week_start).scalar_subquery().label("apps_week"),
        select(func.count(Application.id)).where(Application.applied_at >= prev_week_start, Application.applied_at < week_start).scalar_subquery().label("apps_prev_week"),
        select(func.count(Application.id)).where(Application.applied_at >= thirty_days_ago).scalar_subquery().label("apps_30d"),
        select(func.count(Application.id)).where(Application.applied_at >= sixty_days_ago, Application.applied_at < thirty_days_ago).scalar_subquery().label("apps_prev_30d"),
        # Funnel stages — applications submitted in the selected reporting period
        select(func.count(Application.id)).where(Application.applied_at >= day_start, Application.applied_at < day_end).scalar_subquery().label("period_applied"),
        select(func.count(Application.id)).where(Application.applied_at >= day_start, Application.applied_at < day_end, Application.status == ApplicationStatus.shortlisted).scalar_subquery().label("period_shortlisted"),
        select(func.count(Application.id)).where(Application.applied_at >= day_start, Application.applied_at < day_end, Application.status == ApplicationStatus.interviewing).scalar_subquery().label("period_interviewing"),
        select(func.count(Application.id)).where(Application.applied_at >= day_start, Application.applied_at < day_end, Application.status == ApplicationStatus.selected).scalar_subquery().label("period_selected"),
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.rejected).scalar_subquery().label("all_time_rejected"),
        select(func.count(Interview.id)).where(Interview.scheduled_at >= day_start, Interview.scheduled_at < day_end).scalar_subquery().label("period_interviews"),
        select(func.count(AIInterviewSession.id)).where(AIInterviewSession.status == "completed", AIInterviewSession.created_at >= day_start, AIInterviewSession.created_at < day_end).scalar_subquery().label("period_ai_interviews_done"),
    )

    # Query 3: Score Distribution (5 counts in a single query)
    score_dist_query = select(
        func.coalesce(func.sum(case((Match.score >= 90, 1), else_=0)), 0).label("above_90"),
        func.coalesce(func.sum(case((and_(Match.score >= 80, Match.score < 90), 1), else_=0)), 0).label("range_80_90"),
        func.coalesce(func.sum(case((and_(Match.score >= 70, Match.score < 80), 1), else_=0)), 0).label("range_70_80"),
        func.coalesce(func.sum(case((and_(Match.score >= 60, Match.score < 70), 1), else_=0)), 0).label("range_60_70"),
        func.coalesce(func.sum(case((Match.score < 60, 1), else_=0)), 0).label("below_60")
    )

    # Query 4: Match Trends and stats (10 counts/averages in a single query)
    match_stats_query = select(
        func.coalesce(func.avg(Match.score), 0).label("avg_score"),
        func.coalesce(func.max(Match.score), 0).label("top_score"),
        func.coalesce(func.sum(case((Match.score >= 90, 1), else_=0)), 0).label("above_90"),
        func.coalesce(func.sum(case((Match.score >= 80, 1), else_=0)), 0).label("above_80"),
        func.coalesce(func.sum(case((Match.score >= 70, 1), else_=0)), 0).label("above_70"),
        # Last 30 days
        func.coalesce(func.sum(case((Match.created_at >= thirty_days_ago, 1), else_=0)), 0).label("matches_last_30"),
        func.coalesce(func.avg(case((Match.created_at >= thirty_days_ago, Match.score), else_=None)), 0).label("avg_last_30"),
        func.coalesce(func.sum(case((and_(Match.created_at >= thirty_days_ago, Match.score >= 90), 1), else_=0)), 0).label("above_90_last"),
        func.coalesce(func.sum(case((and_(Match.created_at >= thirty_days_ago, Match.score >= 80), 1), else_=0)), 0).label("above_80_last"),
        func.coalesce(func.sum(case((and_(Match.created_at >= thirty_days_ago, Match.score >= 70), 1), else_=0)), 0).label("above_70_last"),
        # Prev 30 days
        func.coalesce(func.sum(case((and_(Match.created_at >= sixty_days_ago, Match.created_at < thirty_days_ago), 1), else_=0)), 0).label("matches_prev_30"),
        func.coalesce(func.avg(case((and_(Match.created_at >= sixty_days_ago, Match.created_at < thirty_days_ago), Match.score), else_=None)), 0).label("avg_prev_30"),
        func.coalesce(func.sum(case((and_(Match.created_at >= sixty_days_ago, Match.created_at < thirty_days_ago, Match.score >= 90), 1), else_=0)), 0).label("above_90_prev"),
        func.coalesce(func.sum(case((and_(Match.created_at >= sixty_days_ago, Match.created_at < thirty_days_ago, Match.score >= 80), 1), else_=0)), 0).label("above_80_prev"),
        func.coalesce(func.sum(case((and_(Match.created_at >= sixty_days_ago, Match.created_at < thirty_days_ago, Match.score >= 70), 1), else_=0)), 0).label("above_70_prev"),
    )

    # Query 5: Industry match analysis
    industry_match_query = (
        select(JobPosting.industry, func.avg(Match.score).label("avg_score"), func.count(Match.id).label("cnt"))
        .select_from(Match)
        .join(JobPosting, Match.job_id == JobPosting.id)
        .where(JobPosting.industry.isnot(None), JobPosting.industry != "")
        .group_by(JobPosting.industry)
        .order_by(func.avg(Match.score).desc())
        .limit(8)
    )

    # Query 6: Gaps limit 500
    gap_query = select(Match.gaps).where(Match.gaps.isnot(None)).limit(500)

    # Query 7, 8, 9: Candidate growth series (within selected period)
    growth_daily_query = (
        select(func.date_trunc("day", User.created_at).label("period"), func.count(User.id))
        .where(User.is_super_admin.is_(False), User.role == UserRole.seeker, User.created_at >= day_start, User.created_at < day_end)
        .group_by("period")
        .order_by("period")
    )

    growth_weekly_query = (
        select(func.date_trunc("week", User.created_at).label("period"), func.count(User.id))
        .where(User.is_super_admin.is_(False), User.role == UserRole.seeker, User.created_at >= day_start, User.created_at < day_end)
        .group_by("period")
        .order_by("period")
    )

    growth_monthly_query = (
        select(func.date_trunc("month", User.created_at).label("period"), func.count(User.id))
        .where(User.is_super_admin.is_(False), User.role == UserRole.seeker, User.created_at >= day_start, User.created_at < day_end)
        .group_by("period")
        .order_by("period")
    )

    # Provider growth series (within selected period)
    provider_growth_daily_query = (
        select(func.date_trunc("day", User.created_at).label("period"), func.count(User.id))
        .where(User.is_super_admin.is_(False), User.role == UserRole.provider, User.created_at >= day_start, User.created_at < day_end)
        .group_by("period")
        .order_by("period")
    )
    provider_growth_weekly_query = (
        select(func.date_trunc("week", User.created_at).label("period"), func.count(User.id))
        .where(User.is_super_admin.is_(False), User.role == UserRole.provider, User.created_at >= day_start, User.created_at < day_end)
        .group_by("period")
        .order_by("period")
    )
    provider_growth_monthly_query = (
        select(func.date_trunc("month", User.created_at).label("period"), func.count(User.id))
        .where(User.is_super_admin.is_(False), User.role == UserRole.provider, User.created_at >= day_start, User.created_at < day_end)
        .group_by("period")
        .order_by("period")
    )

    # Query 10: Seeker experience distribution (SQL group-by)
    exp_query = (
        select(User.experience, func.count(User.id))
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
        .group_by(User.experience)
    )

    # Query 11: Seeker industry distribution
    industry_query = (
        select(User.industry, func.count(User.id))
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False), User.industry.isnot(None), User.industry != "")
        .group_by(User.industry)
        .order_by(func.count(User.id).desc())
        .limit(10)
    )

    # Query 12: Skills count optimization (sample recent portfolios only)
    skills_query = (
        select(Portfolio.skills)
        .where(Portfolio.skills.isnot(None))
        .order_by(Portfolio.updated_at.desc().nullslast(), Portfolio.user_id.desc())
        .limit(500)
    )

    # Query 13: Recruiter active table (applications in period)
    recruiter_query = (
        select(
            Provider.company_name,
            Provider.first_name,
            Provider.last_name,
            func.count(Application.id).label("app_count"),
        )
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .join(Provider, JobPosting.provider_id == Provider.id)
        .where(Application.applied_at >= day_start, Application.applied_at < day_end)
        .group_by(Provider.id, Provider.company_name, Provider.first_name, Provider.last_name)
        .order_by(func.count(Application.id).desc())
        .limit(8)
    )

    # Query 14: Latest seekers in period
    latest_seeker_query = (
        select(User.first_name, User.last_name, User.email, User.industry, User.created_at, User.is_verified)
        .where(
            User.role == UserRole.seeker,
            User.is_super_admin.is_(False),
            User.created_at >= day_start,
            User.created_at < day_end,
        )
        .order_by(User.created_at.desc())
        .limit(6)
    )

    # Query 15: Recent jobs
    recent_job_query = (
        select(JobPosting.title, JobPosting.industry, JobPosting.is_active, JobPosting.created_at, Provider.company_name)
        .join(Provider, JobPosting.provider_id == Provider.id)
        .order_by(JobPosting.created_at.desc())
        .limit(6)
    )

    # Query 16: Recent applications in period
    recent_app_query = (
        select(
            Application.status,
            Application.applied_at,
            Seeker.first_name,
            Seeker.last_name,
            Seeker.email,
            Application.candidate_name,
            JobPosting.title,
        )
        .outerjoin(Seeker, Application.seeker_id == Seeker.id)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .where(Application.applied_at >= day_start, Application.applied_at < day_end)
        .order_by(Application.applied_at.desc())
        .limit(6)
    )

    # Query 17: Seeker profile completion details (fetch once, specific raw columns)
    profile_query = (
        select(
            User.created_at,
            User.first_name,
            User.last_name,
            User.email,
            User.is_assessment_done,
            Portfolio.headline,
            Portfolio.bio,
            Portfolio.city,
            Portfolio.state,
            Portfolio.linkedin_url,
            Portfolio.github_url,
            Portfolio.website_url,
            Portfolio.skills,
            Portfolio.work_experiences,
            Portfolio.education,
            Portfolio.certifications,
            Portfolio.languages,
            Portfolio.projects,
            Portfolio.intro_video_path,
            Portfolio.intro_audio_path,
            Portfolio.user_id
        )
        .outerjoin(Portfolio, Portfolio.user_id == User.id)
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
        .order_by(User.created_at.desc())
        .limit(1000)
    )

    # ── 2. Run All Queries in Parallel using asyncio.gather ──────────────────
    (
        totals_res,
        summary_counts_res,
        score_dist_res,
        match_stats_res,
        industry_match_res,
        gap_res,
        growth_daily_res,
        growth_weekly_res,
        growth_monthly_res,
        provider_growth_daily_res,
        provider_growth_weekly_res,
        provider_growth_monthly_res,
        exp_res,
        industry_res,
        skills_res,
        recruiter_res,
        latest_seeker_res,
        recent_job_res,
        recent_app_res,
        profile_res
    ) = await asyncio.gather(
        db.execute(totals_query),
        db.execute(summary_counts_query),
        db.execute(score_dist_query),
        db.execute(match_stats_query),
        db.execute(industry_match_query),
        db.execute(gap_query),
        db.execute(growth_daily_query),
        db.execute(growth_weekly_query),
        db.execute(growth_monthly_query),
        db.execute(provider_growth_daily_query),
        db.execute(provider_growth_weekly_query),
        db.execute(provider_growth_monthly_query),
        db.execute(exp_query),
        db.execute(industry_query),
        db.execute(skills_query),
        db.execute(recruiter_query),
        db.execute(latest_seeker_query),
        db.execute(recent_job_query),
        db.execute(recent_app_query),
        db.execute(profile_query)
    )

    # ── 3. Parse Consolidated Row Results ─────────────────────────────────────
    tot_row = totals_res.one()
    sum_row = summary_counts_res.one()
    score_dist_row = score_dist_res.one()
    match_stats_row = match_stats_res.one()

    # Totals
    total_seekers = tot_row.total_seekers
    total_providers = tot_row.total_providers
    total_jobs = tot_row.total_jobs
    active_jobs = tot_row.active_jobs
    inactive_jobs = total_jobs - active_jobs
    total_applications = tot_row.total_applications
    total_matches = tot_row.total_matches

    # Today vs yesterday KPIs
    new_regs_today = tot_row.new_regs_today
    new_regs_yesterday = tot_row.new_regs_yesterday
    new_seekers_period = tot_row.new_seekers_period
    new_seekers_prev = tot_row.new_seekers_prev
    new_providers_period = tot_row.new_providers_period
    new_providers_prev = tot_row.new_providers_prev
    apps_today = tot_row.apps_today
    apps_yesterday = tot_row.apps_yesterday
    interviews_today = tot_row.interviews_today
    interviews_yesterday = tot_row.interviews_yesterday
    matches_today = tot_row.matches_today
    matches_yesterday = tot_row.matches_yesterday
    selections_today = tot_row.selections_today
    selections_yesterday = tot_row.selections_yesterday
    companies_active = tot_row.companies_active
    companies_active_yesterday = tot_row.companies_active_yesterday or companies_active
    active_jobs_yesterday = tot_row.active_jobs_yesterday or active_jobs
    active_companies = companies_active


    # Summary counts
    active_seekers = sum_row.active_seekers
    seekers_30d = sum_row.seekers_30d
    seekers_prev_30d = sum_row.seekers_prev_30d
    providers_30d = sum_row.providers_30d
    providers_prev_30d = sum_row.providers_prev_30d
    hiring_companies = sum_row.hiring_companies
    hiring_companies_prev = sum_row.hiring_companies_prev
    jobs_30d = sum_row.jobs_30d
    jobs_prev_30d = sum_row.jobs_prev_30d
    featured_jobs = sum_row.featured_jobs
    featured_prev = sum_row.featured_prev
    inactive_prev = sum_row.inactive_prev or inactive_jobs
    apps_week = sum_row.apps_week
    apps_prev_week = sum_row.apps_prev_week
    apps_30d = sum_row.apps_30d
    apps_prev_30d = sum_row.apps_prev_30d

    # Funnel (selected reporting period)
    period_applied = sum_row.period_applied
    period_shortlisted = sum_row.period_shortlisted
    period_interviewing = sum_row.period_interviewing
    period_selected = sum_row.period_selected
    all_time_rejected = sum_row.all_time_rejected
    period_interviews = sum_row.period_interviews
    period_ai_interviews_done = sum_row.period_ai_interviews_done

    # ── 4. Process Profile Completion (Once, No Heavy ORM objects) ────────────
    completion_pcts = []
    established_pcts = []
    incomplete_profiles = 0

    for row in profile_res.all():
        pct = _calculate_completion_raw(
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            is_assessment_done=bool(row.is_assessment_done),
            has_portfolio=row.user_id is not None,
            headline=row.headline,
            bio=row.bio,
            city=row.city,
            state=row.state,
            linkedin_url=row.linkedin_url,
            github_url=row.github_url,
            website_url=row.website_url,
            skills=row.skills,
            work_experiences=row.work_experiences,
            education=row.education,
            certifications=row.certifications,
            languages=row.languages,
            projects=row.projects,
            intro_video_path=row.intro_video_path,
            intro_audio_path=row.intro_audio_path
        )
        completion_pcts.append(pct)
        if pct < 50:
            incomplete_profiles += 1
        if row.created_at and row.created_at < thirty_days_ago:
            established_pcts.append(pct)

    profile_rate = round(sum(completion_pcts) / len(completion_pcts), 1) if completion_pcts else 0
    established_rate = round(sum(established_pcts) / len(established_pcts), 1) if established_pcts else profile_rate
    profile_rate_trend = round(profile_rate - established_rate, 1)

    # ── 5. Build Final Response Structures ────────────────────────────────────
    kpi_labels = _kpi_labels(day_start, day_end)
    today_kpis = [
        {
            "key": "new_registrations",
            "label": kpi_labels["new_registrations"],
            "value": new_regs_today,
            "trend": _pct_change(new_regs_today, new_regs_yesterday),
        },
        {
            "key": "active_jobs",
            "label": kpi_labels["active_jobs"],
            "value": active_jobs,
            "trend": _pct_change(active_jobs, active_jobs_yesterday),
        },
        {
            "key": "applications_today",
            "label": kpi_labels["applications"],
            "value": apps_today,
            "trend": _pct_change(apps_today, apps_yesterday),
        },
        {
            "key": "interviews_today",
            "label": kpi_labels["interviews"],
            "value": interviews_today,
            "trend": _pct_change(interviews_today, interviews_yesterday),
        },
        {
            "key": "new_matches",
            "label": kpi_labels["new_matches"],
            "value": matches_today,
            "trend": _pct_change(matches_today, matches_yesterday),
        },
        {
            "key": "selections_today",
            "label": kpi_labels["selections"],
            "value": selections_today,
            "trend": _pct_change(selections_today, selections_yesterday),
        },
        {
            "key": "companies_active",
            "label": kpi_labels["companies_active"],
            "value": companies_active,
            "trend": _pct_change(companies_active, companies_active_yesterday),
        },
    ]

    def _fmt(n: int) -> str:
        return f"{n:,}"

    summary_columns = {
        "users": [
            {"label": "Total Job Seekers", "value": _fmt(total_seekers)},
            {"label": "Active Job Seekers", "value": _fmt(active_seekers)},
            {"label": "Profile Completion Rate", "value": f"{profile_rate}%", "trend": profile_rate_trend},
            {"label": "New Seekers in Period", "value": _fmt(new_seekers_period), "trend": _pct_change(new_seekers_period, new_seekers_prev)},
        ],
        "providers": [
            {"label": "Total Companies", "value": _fmt(total_providers)},
            {"label": "Active Companies", "value": _fmt(active_companies)},
            {"label": "New Companies in Period", "value": _fmt(new_providers_period), "trend": _pct_change(new_providers_period, new_providers_prev)},
            {"label": "Hiring Companies", "value": _fmt(hiring_companies), "trend": _pct_change(hiring_companies, hiring_companies_prev)},
        ],
        "jobs": [
            {"label": "Total Jobs", "value": _fmt(total_jobs)},
            {"label": "Active Jobs", "value": _fmt(active_jobs)},
            {"label": "Expired Jobs", "value": _fmt(inactive_jobs), "trend": _pct_change(inactive_jobs, inactive_prev)},
            {"label": "Featured Jobs", "value": _fmt(featured_jobs), "trend": _pct_change(featured_jobs, featured_prev)},
        ],
        "applications": [
            {"label": "Total Applications (All Time)", "value": _fmt(total_applications)},
            {"label": kpi_labels["applications"], "value": _fmt(apps_today), "trend": _pct_change(apps_today, apps_yesterday)},
            {"label": kpi_labels["interviews"], "value": _fmt(interviews_today), "trend": _pct_change(interviews_today, interviews_yesterday)},
        ],
    }

    funnel_base = max(period_applied, 1)
    shortlisted_count = period_shortlisted
    scheduled_count = period_interviews
    interview_count = max(period_interviewing, period_ai_interviews_done)
    recruitment_funnel = [
        {"stage": "Applied", "count": period_applied, "pct": 100.0 if period_applied else 0.0},
        {"stage": "Shortlisted", "count": shortlisted_count, "pct": _funnel_pct(shortlisted_count, funnel_base)},
        {"stage": "Scheduled", "count": scheduled_count, "pct": _funnel_pct(scheduled_count, funnel_base)},
        {"stage": "Interview", "count": interview_count, "pct": _funnel_pct(interview_count, funnel_base)},
        {"stage": "Selected", "count": period_selected, "pct": _funnel_pct(period_selected, funnel_base)},
    ]
    funnel_velocity = [
        {"label": "Shortlist Rate", "value": _funnel_pct(shortlisted_count, funnel_base), "badge": "Applied → Shortlisted", "tone": "blue"},
        {"label": "Schedule Rate", "value": _funnel_pct(scheduled_count, funnel_base), "badge": "Shortlisted → Scheduled", "tone": "purple"},
        {"label": "Selection Rate", "value": _funnel_pct(period_selected, funnel_base), "badge": "Interview → Selected", "tone": "green"},
    ]
    above_80_matches = int(match_stats_row.above_80 or 0)
    funnel_highlight = None
    if total_matches > 0 and above_80_matches > 0:
        high_share = round((above_80_matches / total_matches) * 100, 1)
        funnel_highlight = (
            f"Funnel Highlight: Candidates with AI Match Score ≥ 80% represent {high_share}% of all matches "
            "and move faster through interview and selection stages."
        )

    # AI Matching stats and score distribution
    total_scored = (
        score_dist_row.above_90 +
        score_dist_row.range_80_90 +
        score_dist_row.range_70_80 +
        score_dist_row.range_60_70 +
        score_dist_row.below_60
    ) or 1

    score_brackets = [
        {"range": "90-100%", "count": score_dist_row.above_90, "pct": round((score_dist_row.above_90 / total_scored) * 100, 1)},
        {"range": "80-90%", "count": score_dist_row.range_80_90, "pct": round((score_dist_row.range_80_90 / total_scored) * 100, 1)},
        {"range": "70-80%", "count": score_dist_row.range_70_80, "pct": round((score_dist_row.range_70_80 / total_scored) * 100, 1)},
        {"range": "60-70%", "count": score_dist_row.range_60_70, "pct": round((score_dist_row.range_60_70 / total_scored) * 100, 1)},
        {"range": "Below 60%", "count": score_dist_row.below_60, "pct": round((score_dist_row.below_60 / total_scored) * 100, 1)},
    ]

    stat_cards = [
        {"key": "total_matches", "label": "Total AI Matches", "value": f"{total_matches:,}", "trend": _pct_change(match_stats_row.matches_last_30, match_stats_row.matches_prev_30)},
    ]

    industry_match_analysis = [
        {"industry": r.industry or "Other", "avg_score": round(float(r.avg_score or 0), 1), "count": r.cnt}
        for r in industry_match_res.all()
    ]

    gap_counter: Counter = Counter()
    for (gaps,) in gap_res.all():
        if isinstance(gaps, list):
            for g in gaps:
                if isinstance(g, str) and g.strip():
                    gap_counter[g.strip()] += 1
    gap_total = sum(gap_counter.values()) or 1
    skill_gap_analysis = [
        {"skill": k, "count": v, "pct": round((v / gap_total) * 100, 1)}
        for k, v in gap_counter.most_common(6)
    ]

    ai_matching = {
        "total_matches": total_matches,
        "avg_score": round(float(match_stats_row.avg_score), 1),
        "top_score": round(float(match_stats_row.top_score), 1),
        "above_90": match_stats_row.above_90,
        "above_80": match_stats_row.above_80,
        "above_70": match_stats_row.above_70,
        "stat_cards": stat_cards,
        "score_distribution": score_brackets,
        "industry_analysis": industry_match_analysis,
        "skill_gaps": skill_gap_analysis,
    }

    # Growth charts
    candidate_growth = {
        "daily": [{"date": r[0].strftime("%Y-%m-%d") if r[0] else "", "count": r[1]} for r in growth_daily_res.all()],
        "weekly": [{"date": r[0].strftime("%Y-%m-%d") if r[0] else "", "count": r[1]} for r in growth_weekly_res.all()],
        "monthly": [{"date": r[0].strftime("%Y-%m-%d") if r[0] else "", "count": r[1]} for r in growth_monthly_res.all()],
    }
    provider_growth = {
        "daily": [{"date": r[0].strftime("%Y-%m-%d") if r[0] else "", "count": r[1]} for r in provider_growth_daily_res.all()],
        "weekly": [{"date": r[0].strftime("%Y-%m-%d") if r[0] else "", "count": r[1]} for r in provider_growth_weekly_res.all()],
        "monthly": [{"date": r[0].strftime("%Y-%m-%d") if r[0] else "", "count": r[1]} for r in provider_growth_monthly_res.all()],
    }

    # Experience breakdown
    exp_counter: Counter = Counter()
    for exp, count in exp_res.all():
        key = (exp or "Not specified").strip()
        if not key:
            key = "Not specified"
        exp_lower = key.lower()
        if "fresher" in exp_lower or "0" in exp_lower:
            bucket = "Freshers"
        elif any(x in exp_lower for x in ["1", "2", "3"]) and "5" not in exp_lower:
            bucket = "1-3 Yrs"
        elif any(x in exp_lower for x in ["3", "4", "5"]):
            bucket = "3-5 Yrs"
        else:
            bucket = "5+ Yrs"
        exp_counter[bucket] += count
    exp_total = sum(exp_counter.values()) or 1
    experience_breakdown = [
        {"level": k, "count": v, "pct": round((v / exp_total) * 100, 1)}
        for k, v in exp_counter.most_common()
    ]

    # Industry distribution
    ind_total = total_seekers or 1
    industry_distribution = [
        {"industry": r[0] or "Other", "count": r[1], "pct": round((r[1] / ind_total) * 100, 1)}
        for r in industry_res.all()
    ]

    # Top skills
    skill_counter: Counter = Counter()
    for (skills,) in skills_res.all():
        if isinstance(skills, list):
            for s in skills:
                name = s.get("name") if isinstance(s, dict) else str(s)
                if name and name.strip():
                    skill_counter[name.strip()] += 1
    top_skills = [{"skill": k, "count": v} for k, v in skill_counter.most_common(20)]

    # Recruiter table
    active_recruiters = [
        {
            "name": r.company_name or f"{r.first_name or ''} {r.last_name or ''}".strip() or "Provider",
            "applications": r.app_count,
        }
        for r in recruiter_res.all()
    ]

    # Latest seekers
    latest_seekers = [
        {
            "name": f"{r.first_name or ''} {r.last_name or ''}".strip() or r.email or "Seeker",
            "industry": r.industry or "—",
            "status": "Verified" if r.is_verified else "Pending",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in latest_seeker_res.all()
    ]

    # Recent jobs
    recent_jobs = [
        {
            "title": r.title,
            "company": r.company_name or "—",
            "industry": r.industry or "—",
            "status": "Active" if r.is_active else "Inactive",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_job_res.all()
    ]

    # Recent applications
    recent_applications = [
        {
            "candidate": f"{r.first_name or ''} {r.last_name or ''}".strip() or r.candidate_name or r.email or "Guest",
            "job": r.title,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "applied_at": r.applied_at.isoformat() if r.applied_at else None,
        }
        for r in recent_app_res.all()
    ]

    # Activity feed
    activity = []
    for s in latest_seekers[:4]:
        activity.append({"type": "registration", "message": f"New candidate {s['name']} registered", "time": s["created_at"]})
    for a in recent_applications[:4]:
        activity.append({"type": "application", "message": f"{a['candidate']} applied for {a['job']}", "time": a["applied_at"]})
    activity.sort(key=lambda x: x.get("time") or "", reverse=True)
    activity = activity[:8]

    # System alerts
    system_alerts = []
    if inactive_jobs > 0:
        system_alerts.append({"level": "error", "message": f"{inactive_jobs} jobs are inactive/expired"})
    if incomplete_profiles > 0:
        system_alerts.append({"level": "warning", "message": f"{incomplete_profiles} candidates have incomplete profiles"})
    if all_time_rejected > 0:
        system_alerts.append({"level": "info", "message": f"{all_time_rejected} applications were rejected"})

    platform_overview = [
        {"label": "Total Users", "value": total_seekers + total_providers, "trend": _pct_change(new_regs_today, new_regs_yesterday)},
        {"label": "Companies", "value": total_providers, "trend": _pct_change(new_providers_period, new_providers_prev)},
        {"label": "Jobs", "value": active_jobs, "trend": _pct_change(active_jobs, active_jobs_yesterday)},
        {"label": "Applications", "value": apps_today, "trend": _pct_change(apps_today, apps_yesterday)},
    ]

    period_end_inclusive = day_end - timedelta(days=1)
    reporting_period = {
        "start_date": day_start.date().isoformat(),
        "end_date": period_end_inclusive.date().isoformat(),
    }

    return {
        "generated_at": now.isoformat(),
        "reporting_period": reporting_period,
        "today_kpis": today_kpis,
        "summary_columns": summary_columns,
        "recruitment_funnel": recruitment_funnel,
        "funnel_velocity": funnel_velocity,
        "funnel_highlight": funnel_highlight,
        "ai_matching": ai_matching,
        "candidate_growth": candidate_growth,
        "provider_growth": provider_growth,
        "experience_breakdown": experience_breakdown,
        "industry_distribution": industry_distribution,
        "top_skills": top_skills,
        "active_recruiters": active_recruiters,
        "latest_seekers": latest_seekers,
        "recent_jobs": recent_jobs,
        "recent_applications": recent_applications,
        "recent_activity": activity,
        "system_alerts": system_alerts,
        "platform_overview": platform_overview,
    }

