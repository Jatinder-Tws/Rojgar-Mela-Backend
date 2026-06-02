"""Platform-wide analytics for super admin transparency dashboard."""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.application import Application, ApplicationStatus
from models.interview import Interview
from models.job import JobPosting
from models.match import Match
from models.portfolio import Portfolio
from models.user import User, UserRole
from services.portfolio_service import calculate_completion


async def get_detailed_platform_analytics(db: AsyncSession) -> dict:
    Seeker = aliased(User)
    Provider = aliased(User)

    total_seekers = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
    ) or 0
    total_providers = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.provider, User.is_super_admin.is_(False))
    ) or 0

    seekers_onboarded = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.seeker,
            User.is_super_admin.is_(False),
            User.onboarding_complete.is_(True),
        )
    ) or 0

    seekers_with_portfolio = await db.scalar(
        select(func.count(Portfolio.id))
        .select_from(Portfolio)
        .join(User, Portfolio.user_id == User.id)
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
    ) or 0

    seeker_rows = await db.execute(
        select(User, Portfolio)
        .outerjoin(Portfolio, Portfolio.user_id == User.id)
        .where(User.role == UserRole.seeker, User.is_super_admin.is_(False))
    )
    profile_complete_80 = 0
    profile_complete_50 = 0
    profile_low = 0
    for user, portfolio in seeker_rows.all():
        if not portfolio:
            profile_low += 1
            continue
        pct, _, _ = calculate_completion(portfolio, user)
        if pct >= 80:
            profile_complete_80 += 1
        elif pct >= 50:
            profile_complete_50 += 1
        else:
            profile_low += 1

    apps_by_status = {}
    apps_result = await db.execute(
        select(Application.status, func.count(Application.id)).group_by(Application.status)
    )
    for status, count in apps_result.all():
        key = status.value if hasattr(status, "value") else str(status)
        apps_by_status[key] = count

    total_shortlisted = apps_by_status.get("shortlisted", 0)
    total_rejected = apps_by_status.get("rejected", 0)
    total_applied = apps_by_status.get("applied", 0) + apps_by_status.get("auto_applied", 0)
    total_interviews = await db.scalar(select(func.count(Interview.id))) or 0
    total_matches = await db.scalar(select(func.count(Match.id))) or 0

    shortlist_rows = await db.execute(
        select(
            Application.id,
            Application.updated_at,
            Application.status,
            Seeker.first_name,
            Seeker.last_name,
            Seeker.email,
            JobPosting.title,
            Provider.company_name,
            Provider.first_name,
            Provider.last_name,
            Provider.email,
        )
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .join(Provider, JobPosting.provider_id == Provider.id)
        .outerjoin(Seeker, Application.seeker_id == Seeker.id)
        .where(Application.status == ApplicationStatus.shortlisted)
        .order_by(Application.updated_at.desc())
        .limit(100)
    )

    recent_shortlists = []
    for (
        app_id,
        updated_at,
        status,
        s_fn,
        s_ln,
        s_email,
        job_title,
        co_name,
        p_fn,
        p_ln,
        p_email,
    ) in shortlist_rows.all():
        provider_name = co_name or f"{p_fn or ''} {p_ln or ''}".strip() or p_email or "Provider"
        seeker_name = f"{s_fn or ''} {s_ln or ''}".strip() or s_email or "Guest applicant"
        recent_shortlists.append(
            {
                "application_id": app_id,
                "seeker_name": seeker_name,
                "seeker_email": s_email,
                "job_title": job_title,
                "provider_name": provider_name,
                "provider_email": p_email,
                "status": status.value if hasattr(status, "value") else str(status),
                "updated_at": updated_at.isoformat() if updated_at else None,
            }
        )

    provider_leaderboard = await db.execute(
        select(
            Provider.id,
            Provider.company_name,
            Provider.first_name,
            Provider.last_name,
            func.count(Application.id).label("shortlist_count"),
        )
        .select_from(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .join(Provider, JobPosting.provider_id == Provider.id)
        .where(Application.status == ApplicationStatus.shortlisted)
        .group_by(Provider.id, Provider.company_name, Provider.first_name, Provider.last_name)
        .order_by(func.count(Application.id).desc())
        .limit(20)
    )

    top_providers_shortlisting = [
        {
            "provider_id": r.id,
            "provider_name": r.company_name or f"{r.first_name or ''} {r.last_name or ''}".strip(),
            "shortlist_count": r.shortlist_count,
        }
        for r in provider_leaderboard.all()
    ]

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    shortlists_30d = await db.scalar(
        select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.shortlisted,
            Application.updated_at >= thirty_days_ago,
        )
    ) or 0

    return {
        "total_seekers": total_seekers,
        "total_providers": total_providers,
        "seekers_onboarded": seekers_onboarded,
        "seekers_with_portfolio": seekers_with_portfolio,
        "seekers_without_portfolio": max(0, total_seekers - seekers_with_portfolio),
        "profile_completion": {
            "complete_80_plus": profile_complete_80,
            "partial_50_to_79": profile_complete_50,
            "low_under_50": profile_low,
        },
        "hiring_pipeline": {
            "total_applications": sum(apps_by_status.values()),
            "applied": total_applied,
            "shortlisted": total_shortlisted,
            "rejected": total_rejected,
            "interviews_scheduled": total_interviews,
            "ai_matches": total_matches,
            "shortlisted_last_30_days": shortlists_30d,
        },
        "applications_by_status": apps_by_status,
        "recent_shortlists": recent_shortlists,
        "top_providers_by_shortlists": top_providers_shortlisting,
    }
