"""Comprehensive dashboard analytics for super admin."""
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.application import Application, ApplicationStatus
from models.ai_interview import AIInterviewSession
from models.interview import Interview
from models.job import JobPosting
from models.match import Match
from models.portfolio import Portfolio
from models.user import User, UserRole
from services.portfolio_service import calculate_completion


def _pct_change(today: int, yesterday: int) -> float:
    if yesterday == 0:
        return 100.0 if today > 0 else 0.0
    return round(((today - yesterday) / yesterday) * 100, 1)


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


async def get_dashboard_analytics(
    db: AsyncSession,
    target_date: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    now = end_date or target_date or datetime.utcnow()
    day_start, day_end, yesterday_start, yesterday_end = _resolve_period_bounds(
        target_date, start_date, end_date
    )

    Seeker = aliased(User)
    Provider = aliased(User)

    # ── Totals ───────────────────────────────────────────────────────────────
    total_seekers = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
    ) or 0
    total_providers = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False))
    ) or 0
    total_jobs = await db.scalar(select(func.count(JobPosting.id))) or 0
    active_jobs = await db.scalar(select(func.count(JobPosting.id)).where(JobPosting.is_active.is_(True))) or 0
    inactive_jobs = total_jobs - active_jobs
    total_applications = await db.scalar(select(func.count(Application.id))) or 0
    total_matches = await db.scalar(select(func.count(Match.id))) or 0

    # ── Today vs yesterday KPIs ─────────────────────────────────────────────
    new_regs_today = await db.scalar(
        select(func.count(User.id)).where(
            User.is_super_admin.is_(False),
            User.created_at >= day_start,
            User.created_at < day_end,
        )
    ) or 0
    new_regs_yesterday = await db.scalar(
        select(func.count(User.id)).where(
            User.is_super_admin.is_(False),
            User.created_at >= yesterday_start,
            User.created_at < yesterday_end,
        )
    ) or 0

    apps_today = await db.scalar(
        select(func.count(Application.id)).where(
            Application.applied_at >= day_start,
            Application.applied_at < day_end,
        )
    ) or 0
    apps_yesterday = await db.scalar(
        select(func.count(Application.id)).where(
            Application.applied_at >= yesterday_start,
            Application.applied_at < yesterday_end,
        )
    ) or 0

    interviews_today = await db.scalar(
        select(func.count(Interview.id)).where(
            Interview.scheduled_at >= day_start,
            Interview.scheduled_at < day_end,
        )
    ) or 0
    interviews_yesterday = await db.scalar(
        select(func.count(Interview.id)).where(
            Interview.scheduled_at >= yesterday_start,
            Interview.scheduled_at < yesterday_end,
        )
    ) or 0

    matches_today = await db.scalar(
        select(func.count(Match.id)).where(
            Match.created_at >= day_start,
            Match.created_at < day_end,
        )
    ) or 0
    matches_yesterday = await db.scalar(
        select(func.count(Match.id)).where(
            Match.created_at >= yesterday_start,
            Match.created_at < yesterday_end,
        )
    ) or 0

    selections_today = await db.scalar(
        select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.shortlisted,
            Application.updated_at >= day_start,
            Application.updated_at < day_end,
        )
    ) or 0
    selections_yesterday = await db.scalar(
        select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.shortlisted,
            Application.updated_at >= yesterday_start,
            Application.updated_at < yesterday_end,
        )
    ) or 0

    companies_active = await db.scalar(
        select(func.count(func.distinct(JobPosting.provider_id))).where(JobPosting.is_active.is_(True))
    ) or 0
    companies_active_yesterday = await db.scalar(
        select(func.count(func.distinct(JobPosting.provider_id))).where(
            JobPosting.is_active.is_(True),
            JobPosting.updated_at < day_end,
        )
    ) or companies_active

    active_jobs_yesterday = await db.scalar(
        select(func.count(JobPosting.id)).where(
            JobPosting.is_active.is_(True),
            JobPosting.created_at < day_end,
        )
    ) or active_jobs

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

    # ── Summary columns ─────────────────────────────────────────────────────
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    active_seekers = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.seeker,
            User.is_super_admin.is_(False),
            User.onboarding_complete.is_(True),
        )
    ) or 0

    seekers_30d = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.seeker,
            User.is_super_admin.is_(False),
            User.created_at >= thirty_days_ago,
        )
    ) or 0
    seekers_prev_30d = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.seeker,
            User.is_super_admin.is_(False),
            User.created_at >= sixty_days_ago,
            User.created_at < thirty_days_ago,
        )
    ) or 0

    profile_rows = await db.execute(
        select(User, Portfolio)
        .outerjoin(Portfolio, Portfolio.user_id == User.id)
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
    )
    completion_pcts = []
    established_pcts = []
    for user, portfolio in profile_rows.all():
        if not portfolio:
            completion_pcts.append(0)
            continue
        pct, _, _ = calculate_completion(portfolio, user)
        completion_pcts.append(pct)
        if user.created_at and user.created_at < thirty_days_ago:
            established_pcts.append(pct)
    profile_rate = round(sum(completion_pcts) / len(completion_pcts), 1) if completion_pcts else 0
    established_rate = round(sum(established_pcts) / len(established_pcts), 1) if established_pcts else profile_rate
    profile_rate_trend = round(profile_rate - established_rate, 1)

    active_companies = await db.scalar(
        select(func.count(func.distinct(JobPosting.provider_id))).where(JobPosting.is_active.is_(True))
    ) or 0
    providers_30d = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.provider,
            User.is_super_admin.is_(False),
            User.created_at >= thirty_days_ago,
        )
    ) or 0
    providers_prev_30d = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.provider,
            User.is_super_admin.is_(False),
            User.created_at >= sixty_days_ago,
            User.created_at < thirty_days_ago,
        )
    ) or 0
    hiring_companies = await db.scalar(
        select(func.count(func.distinct(JobPosting.provider_id)))
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
    ) or 0
    hiring_companies_prev = await db.scalar(
        select(func.count(func.distinct(JobPosting.provider_id)))
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .where(Application.applied_at < thirty_days_ago)
    ) or 0

    jobs_30d = await db.scalar(
        select(func.count(JobPosting.id)).where(JobPosting.created_at >= thirty_days_ago)
    ) or 0
    jobs_prev_30d = await db.scalar(
        select(func.count(JobPosting.id)).where(
            JobPosting.created_at >= sixty_days_ago,
            JobPosting.created_at < thirty_days_ago,
        )
    ) or 0

    featured_jobs = await db.scalar(
        select(func.count(JobPosting.id)).where(JobPosting.ai_interview_enabled.is_(True))
    ) or 0
    featured_prev = await db.scalar(
        select(func.count(JobPosting.id)).where(
            JobPosting.ai_interview_enabled.is_(True),
            JobPosting.created_at < thirty_days_ago,
        )
    ) or 0
    inactive_prev = await db.scalar(
        select(func.count(JobPosting.id)).where(
            JobPosting.is_active.is_(False),
            JobPosting.updated_at < thirty_days_ago,
        )
    ) or inactive_jobs

    apps_week = await db.scalar(
        select(func.count(Application.id)).where(Application.applied_at >= week_start)
    ) or 0
    apps_prev_week = await db.scalar(
        select(func.count(Application.id)).where(
            Application.applied_at >= prev_week_start,
            Application.applied_at < week_start,
        )
    ) or 0
    apps_30d = await db.scalar(
        select(func.count(Application.id)).where(Application.applied_at >= thirty_days_ago)
    ) or 0
    apps_prev_30d = await db.scalar(
        select(func.count(Application.id)).where(
            Application.applied_at >= sixty_days_ago,
            Application.applied_at < thirty_days_ago,
        )
    ) or 0

    def _fmt(n: int) -> str:
        return f"{n:,}"

    summary_columns = {
        "users": [
            {"label": "Total Job Seekers", "value": _fmt(total_seekers)},
            {"label": "Active Job Seekers", "value": _fmt(active_seekers)},
            {"label": "Profile Completion Rate", "value": f"{profile_rate}%", "trend": profile_rate_trend},
            {"label": "New Seekers This Month", "value": _fmt(seekers_30d), "trend": _pct_change(seekers_30d, seekers_prev_30d)},
        ],
        "providers": [
            {"label": "Total Companies", "value": _fmt(total_providers)},
            {"label": "Active Companies", "value": _fmt(active_companies)},
            {"label": "New Companies", "value": _fmt(providers_30d), "trend": _pct_change(providers_30d, providers_prev_30d)},
            {"label": "Hiring Companies", "value": _fmt(hiring_companies), "trend": _pct_change(hiring_companies, hiring_companies_prev)},
        ],
        "jobs": [
            {"label": "Total Jobs", "value": _fmt(total_jobs)},
            {"label": "Active Jobs", "value": _fmt(active_jobs)},
            {"label": "Expired Jobs", "value": _fmt(inactive_jobs), "trend": _pct_change(inactive_jobs, inactive_prev)},
            {"label": "Featured Jobs", "value": _fmt(featured_jobs), "trend": _pct_change(featured_jobs, featured_prev)},
        ],
        "applications": [
            {"label": "Total Applications", "value": _fmt(total_applications)},
            {"label": kpi_labels["applications"], "value": _fmt(apps_today)},
            {"label": "Applications This Week", "value": _fmt(apps_week), "trend": _pct_change(apps_week, apps_prev_week)},
            {"label": "Applications This Month", "value": _fmt(apps_30d), "trend": _pct_change(apps_30d, apps_prev_30d)},
        ],
    }

    # ── Recruitment funnel ────────────────────────────────────────────────────
    applied = await db.scalar(
        select(func.count(Application.id)).where(
            Application.status.in_([ApplicationStatus.applied, ApplicationStatus.auto_applied])
        )
    ) or 0
    shortlisted = await db.scalar(
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.shortlisted)
    ) or 0
    rejected = await db.scalar(
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.rejected)
    ) or 0
    total_interviews = await db.scalar(select(func.count(Interview.id))) or 0
    ai_interviews_done = await db.scalar(
        select(func.count(AIInterviewSession.id)).where(AIInterviewSession.status == "completed")
    ) or 0

    funnel_base = max(total_applications, 1)
    recruitment_funnel = [
        {"stage": "Applied", "count": total_applications, "pct": 100.0},
        {"stage": "AI Matched", "count": total_matches, "pct": round((total_matches / funnel_base) * 100, 1)},
        {"stage": "Shortlisted", "count": shortlisted, "pct": round((shortlisted / funnel_base) * 100, 1)},
        {"stage": "Interview Scheduled", "count": total_interviews, "pct": round((total_interviews / funnel_base) * 100, 1)},
        {"stage": "Interview Completed", "count": ai_interviews_done, "pct": round((ai_interviews_done / funnel_base) * 100, 1)},
        {"stage": "Selected", "count": shortlisted, "pct": round((shortlisted / funnel_base) * 100, 1)},
        {"stage": "Joined", "count": max(0, shortlisted - rejected), "pct": round((max(0, shortlisted - rejected) / funnel_base) * 100, 1)},
    ]

    # ── AI matching analytics ─────────────────────────────────────────────────
    avg_score = await db.scalar(select(func.avg(Match.score))) or 0
    top_score = await db.scalar(select(func.max(Match.score))) or 0
    above_90 = await db.scalar(select(func.count(Match.id)).where(Match.score >= 90)) or 0
    above_80 = await db.scalar(select(func.count(Match.id)).where(Match.score >= 80)) or 0
    above_70 = await db.scalar(select(func.count(Match.id)).where(Match.score >= 70)) or 0

    score_brackets = [
        {"range": "90-100%", "count": await db.scalar(select(func.count(Match.id)).where(Match.score >= 90)) or 0},
        {"range": "80-90%", "count": await db.scalar(select(func.count(Match.id)).where(and_(Match.score >= 80, Match.score < 90))) or 0},
        {"range": "70-80%", "count": await db.scalar(select(func.count(Match.id)).where(and_(Match.score >= 70, Match.score < 80))) or 0},
        {"range": "60-70%", "count": await db.scalar(select(func.count(Match.id)).where(and_(Match.score >= 60, Match.score < 70))) or 0},
        {"range": "Below 60%", "count": await db.scalar(select(func.count(Match.id)).where(Match.score < 60)) or 0},
    ]
    total_scored = sum(b["count"] for b in score_brackets) or 1
    for b in score_brackets:
        b["pct"] = round((b["count"] / total_scored) * 100, 1)

    industry_match_rows = await db.execute(
        select(JobPosting.industry, func.avg(Match.score).label("avg_score"), func.count(Match.id).label("cnt"))
        .select_from(Match)
        .join(JobPosting, Match.job_id == JobPosting.id)
        .where(JobPosting.industry.isnot(None), JobPosting.industry != "")
        .group_by(JobPosting.industry)
        .order_by(func.avg(Match.score).desc())
        .limit(8)
    )
    industry_match_analysis = [
        {"industry": r.industry or "Other", "avg_score": round(float(r.avg_score or 0), 1), "count": r.cnt}
        for r in industry_match_rows.all()
    ]

    gap_counter: Counter = Counter()
    gap_rows = await db.execute(select(Match.gaps).where(Match.gaps.isnot(None)).limit(500))
    for (gaps,) in gap_rows.all():
        if isinstance(gaps, list):
            for g in gaps:
                if isinstance(g, str) and g.strip():
                    gap_counter[g.strip()] += 1
    gap_total = sum(gap_counter.values()) or 1
    skill_gap_analysis = [
        {"skill": k, "count": v, "pct": round((v / gap_total) * 100, 1)}
        for k, v in gap_counter.most_common(6)
    ]

    # AI matching trends — last 30 days vs previous 30 days
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    async def _match_count_since(since, until=None, min_score=None):
        filters = [Match.created_at >= since]
        if until:
            filters.append(Match.created_at < until)
        if min_score is not None:
            filters.append(Match.score >= min_score)
        return await db.scalar(select(func.count(Match.id)).where(*filters)) or 0

    async def _avg_score_since(since, until=None):
        filters = [Match.created_at >= since]
        if until:
            filters.append(Match.created_at < until)
        val = await db.scalar(select(func.avg(Match.score)).where(*filters))
        return float(val or 0)

    matches_last_30 = await _match_count_since(thirty_days_ago)
    matches_prev_30 = await _match_count_since(sixty_days_ago, thirty_days_ago)
    avg_last_30 = await _avg_score_since(thirty_days_ago)
    avg_prev_30 = await _avg_score_since(sixty_days_ago, thirty_days_ago)
    above_90_last = await _match_count_since(thirty_days_ago, min_score=90)
    above_90_prev = await _match_count_since(sixty_days_ago, thirty_days_ago, min_score=90)
    above_80_last = await _match_count_since(thirty_days_ago, min_score=80)
    above_80_prev = await _match_count_since(sixty_days_ago, thirty_days_ago, min_score=80)
    above_70_last = await _match_count_since(thirty_days_ago, min_score=70)
    above_70_prev = await _match_count_since(sixty_days_ago, thirty_days_ago, min_score=70)

    stat_cards = [
        {"key": "total_matches", "label": "Total AI Matches", "value": f"{total_matches:,}", "trend": _pct_change(matches_last_30, matches_prev_30)},
        {"key": "avg_score", "label": "Average Match Score", "value": f"{round(float(avg_score), 1)}%", "trend": _pct_change(round(avg_last_30, 1), round(avg_prev_30, 1))},
        {"key": "top_score", "label": "Top Match Score", "value": f"{round(float(top_score), 1)}%", "trend": None},
        {"key": "above_90", "label": "Candidates > 90%", "value": f"{above_90:,}", "trend": _pct_change(above_90_last, above_90_prev)},
        {"key": "above_80", "label": "Candidates > 80%", "value": f"{above_80:,}", "trend": _pct_change(above_80_last, above_80_prev)},
        {"key": "above_70", "label": "Candidates > 70%", "value": f"{above_70:,}", "trend": _pct_change(above_70_last, above_70_prev)},
    ]

    ai_matching = {
        "total_matches": total_matches,
        "avg_score": round(float(avg_score), 1),
        "top_score": round(float(top_score), 1),
        "above_90": above_90,
        "above_80": above_80,
        "above_70": above_70,
        "stat_cards": stat_cards,
        "score_distribution": score_brackets,
        "industry_analysis": industry_match_analysis,
        "skill_gaps": skill_gap_analysis,
    }

    # ── Growth charts ─────────────────────────────────────────────────────────
    async def _growth_series(days: int, trunc: str):
        since = now - timedelta(days=days)
        q = (
            select(func.date_trunc(trunc, User.created_at).label("period"), func.count(User.id))
            .where(User.is_super_admin.is_(False), User.role == UserRole.seeker, User.created_at >= since)
            .group_by("period")
            .order_by("period")
        )
        rows = (await db.execute(q)).all()
        return [{"date": r[0].strftime("%Y-%m-%d") if r[0] else "", "count": r[1]} for r in rows]

    candidate_growth = {
        "daily": await _growth_series(30, "day"),
        "weekly": await _growth_series(84, "week"),
        "monthly": await _growth_series(365, "month"),
    }

    # ── Experience breakdown ──────────────────────────────────────────────────
    exp_counter: Counter = Counter()
    seeker_rows = await db.execute(
        select(User.experience)
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
    )
    for (exp,) in seeker_rows.all():
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
        exp_counter[bucket] += 1
    exp_total = sum(exp_counter.values()) or 1
    experience_breakdown = [
        {"level": k, "count": v, "pct": round((v / exp_total) * 100, 1)}
        for k, v in exp_counter.most_common()
    ]

    # ── Industry distribution (seekers) ───────────────────────────────────────
    industry_rows = await db.execute(
        select(User.industry, func.count(User.id))
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False), User.industry.isnot(None), User.industry != "")
        .group_by(User.industry)
        .order_by(func.count(User.id).desc())
        .limit(10)
    )
    ind_total = total_seekers or 1
    industry_distribution = [
        {"industry": r[0] or "Other", "count": r[1], "pct": round((r[1] / ind_total) * 100, 1)}
        for r in industry_rows.all()
    ]

    # ── Top skills from portfolios ────────────────────────────────────────────
    skill_counter: Counter = Counter()
    portfolio_rows = await db.execute(select(Portfolio.skills).where(Portfolio.skills.isnot(None)))
    for (skills,) in portfolio_rows.all():
        if isinstance(skills, list):
            for s in skills:
                name = s.get("name") if isinstance(s, dict) else str(s)
                if name and name.strip():
                    skill_counter[name.strip()] += 1
    top_skills = [{"skill": k, "count": v} for k, v in skill_counter.most_common(20)]

    # ── Data tables ───────────────────────────────────────────────────────────
    recruiter_rows = await db.execute(
        select(
            Provider.company_name,
            Provider.first_name,
            Provider.last_name,
            func.count(Application.id).label("app_count"),
        )
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .join(Provider, JobPosting.provider_id == Provider.id)
        .group_by(Provider.id, Provider.company_name, Provider.first_name, Provider.last_name)
        .order_by(func.count(Application.id).desc())
        .limit(8)
    )
    active_recruiters = [
        {
            "name": r.company_name or f"{r.first_name or ''} {r.last_name or ''}".strip() or "Provider",
            "applications": r.app_count,
        }
        for r in recruiter_rows.all()
    ]

    latest_seeker_rows = await db.execute(
        select(User.first_name, User.last_name, User.email, User.industry, User.created_at, User.is_verified)
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
        .order_by(User.created_at.desc())
        .limit(6)
    )
    latest_seekers = [
        {
            "name": f"{r.first_name or ''} {r.last_name or ''}".strip() or r.email or "Seeker",
            "industry": r.industry or "—",
            "status": "Verified" if r.is_verified else "Pending",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in latest_seeker_rows.all()
    ]

    recent_job_rows = await db.execute(
        select(JobPosting.title, JobPosting.industry, JobPosting.is_active, JobPosting.created_at, Provider.company_name)
        .join(Provider, JobPosting.provider_id == Provider.id)
        .order_by(JobPosting.created_at.desc())
        .limit(6)
    )
    recent_jobs = [
        {
            "title": r.title,
            "company": r.company_name or "—",
            "industry": r.industry or "—",
            "status": "Active" if r.is_active else "Inactive",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_job_rows.all()
    ]

    recent_app_rows = await db.execute(
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
        .order_by(Application.applied_at.desc())
        .limit(6)
    )
    recent_applications = [
        {
            "candidate": f"{r.first_name or ''} {r.last_name or ''}".strip() or r.candidate_name or r.email or "Guest",
            "job": r.title,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "applied_at": r.applied_at.isoformat() if r.applied_at else None,
        }
        for r in recent_app_rows.all()
    ]

    # ── Activity feed ─────────────────────────────────────────────────────────
    activity = []
    for s in latest_seekers[:4]:
        activity.append({"type": "registration", "message": f"New candidate {s['name']} registered", "time": s["created_at"]})
    for a in recent_applications[:4]:
        activity.append({"type": "application", "message": f"{a['candidate']} applied for {a['job']}", "time": a["applied_at"]})
    activity.sort(key=lambda x: x.get("time") or "", reverse=True)
    activity = activity[:8]

    # ── System alerts ─────────────────────────────────────────────────────────
    incomplete_profiles = 0
    profile_rows = await db.execute(
        select(User, Portfolio)
        .outerjoin(Portfolio, Portfolio.user_id == User.id)
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
    )
    for user, portfolio in profile_rows.all():
        if not portfolio:
            incomplete_profiles += 1
            continue
        pct, _, _ = calculate_completion(portfolio, user)
        if pct < 50:
            incomplete_profiles += 1

    system_alerts = []
    if inactive_jobs > 0:
        system_alerts.append({"level": "error", "message": f"{inactive_jobs} jobs are inactive/expired"})
    if incomplete_profiles > 0:
        system_alerts.append({"level": "warning", "message": f"{incomplete_profiles} candidates have incomplete profiles"})
    if rejected > 0:
        system_alerts.append({"level": "info", "message": f"{rejected} applications were rejected"})

    platform_overview = [
        {"label": "Total Users", "value": total_seekers + total_providers, "trend": _pct_change(new_regs_today, new_regs_yesterday)},
        {"label": "Companies", "value": total_providers, "trend": _pct_change(providers_30d, providers_prev_30d)},
        {"label": "Jobs", "value": total_jobs, "trend": _pct_change(jobs_30d, jobs_prev_30d)},
        {"label": "Applications", "value": total_applications, "trend": _pct_change(apps_today, apps_yesterday)},
    ]

    return {
        "generated_at": now.isoformat(),
        "today_kpis": today_kpis,
        "summary_columns": summary_columns,
        "recruitment_funnel": recruitment_funnel,
        "ai_matching": ai_matching,
        "candidate_growth": candidate_growth,
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
