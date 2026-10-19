"""
ORM-based database helpers for job_fairs table.
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

from sqlalchemy import select, or_, func, exists, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.models.job_fair import JobFair, JobFairCompany, JobFairSeeker
from app.modules.jobs_portal.schemas.job_fair import (
    JobFairOut,
    JobFairPublicOut,
    JobFairCompanyLogoOut,
    JobFairPublicCatalogResponse,
)
from app.shared.models.user import User


async def slug_exists_db(
    db: AsyncSession, slug: str, exclude_id: Optional[str] = None
) -> bool:
    q = select(JobFair).where(JobFair.slug == slug)
    if exclude_id:
        q = q.where(JobFair.id != exclude_id)
    q = q.limit(1)
    
    res = await db.execute(q)
    return res.scalar_one_or_none() is not None


async def list_job_fairs_db(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    sort_by: str = "date_asc",
    page: int = 1,
    page_size: int = 12,
) -> tuple[list[JobFairOut], int]:
    # Base query
    q = select(JobFair)
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        q = q.where(
            or_(
                JobFair.title.ilike(search_pattern),
                JobFair.location.ilike(search_pattern)
            )
        )

    # Count total matching records using a subquery
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sort
    order_map = {
        "date_desc": JobFair.date.desc(),
        "title_asc": JobFair.title.asc(),
        "title_desc": JobFair.title.desc(),
        "date_asc": JobFair.date.asc(),
    }
    order_clause = order_map.get(sort_by, JobFair.date.asc())
    q = q.order_by(order_clause)

    # Paginate
    q = q.limit(page_size).offset((page - 1) * page_size)

    res = await db.execute(q)
    fairs = res.scalars().all()

    return [JobFairOut.model_validate(f) for f in fairs], int(total)


def _is_online_location(location: Optional[str]) -> bool:
    loc = (location or "").strip().lower()
    return any(token in loc for token in ("online", "virtual", "remote", "webinar", "zoom"))


def classify_job_fair_status(
    fair_date: datetime,
    end_date_str: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """Classify event status: same calendar day = live, past = concluded, future = upcoming in IST."""
    if now is None:
        now = datetime.now(IST)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc).astimezone(IST)
    else:
        now = now.astimezone(IST)

    today = now.date()

    if fair_date.tzinfo is None:
        fair_ist = fair_date.replace(tzinfo=timezone.utc).astimezone(IST)
    else:
        fair_ist = fair_date.astimezone(IST)

    start_date = fair_ist.date()
    end_date = start_date

    if end_date_str:
        try:
            cleaned = str(end_date_str).strip().split("T")[0].split(" ")[0]
            parts = [int(p) for p in cleaned.split("-")]
            if len(parts) == 3:
                end_date = datetime(parts[0], parts[1], parts[2]).date()
        except Exception:
            pass

    if end_date < today:
        return "concluded"
    if start_date <= today <= end_date:
        return "live"
    return "upcoming"


def _profile_dict(fair) -> dict:
    raw = getattr(fair, "event_profile", None)
    return raw if isinstance(raw, dict) else {}


def _public_profile(fair) -> Optional[dict]:
    profile = _profile_dict(fair)
    return profile or None


def _public_is_online(fair) -> bool:
    mode = _profile_dict(fair).get("mode")
    if mode == "online":
        return True
    if mode in ("offline", "hybrid"):
        return False
    return _is_online_location(getattr(fair, "location", None))


def _public_status(fair, now: datetime) -> str:
    profile = _profile_dict(fair)
    life = profile.get("lifecycle")
    if life == "draft":
        return "draft"
    if life == "completed":
        return "concluded"
    if life == "live":
        return "live"
    return classify_job_fair_status(fair.date, profile.get("endDate"), now)


async def _company_logos_by_fair(
    db: AsyncSession, fair_ids: list[str], per_fair: int = 6
) -> dict[str, list[JobFairCompanyLogoOut]]:
    logos: dict[str, list[JobFairCompanyLogoOut]] = defaultdict(list)
    if not fair_ids:
        return logos

    result = await db.execute(
        select(
            JobFairCompany.job_fair_id,
            JobFairCompany.company_name,
            JobFairCompany.logo_url,
            User.company_name,
            User.profile_pic_url,
        )
        .outerjoin(User, JobFairCompany.provider_id == User.id)
        .where(JobFairCompany.job_fair_id.in_(fair_ids))
        .order_by(JobFairCompany.registered_at.desc())
    )
    for job_fair_id, snap_name, snap_logo, user_name, user_logo in result.all():
        bucket = logos[str(job_fair_id)]
        if len(bucket) >= per_fair:
            continue
        bucket.append(
            JobFairCompanyLogoOut(
                company_name=snap_name or user_name,
                logo_url=snap_logo or user_logo,
            )
        )
    return logos


async def _to_public_out(
    fair: JobFair,
    *,
    company_count: int,
    candidate_count: int,
    logos: list[JobFairCompanyLogoOut],
    now: datetime,
) -> JobFairPublicOut:
    return JobFairPublicOut(
        id=str(fair.id),
        slug=fair.slug,
        title=fair.title,
        description=fair.description,
        date=fair.date,
        location=fair.location,
        banner_image_url=fair.banner_image_url,
        is_active=bool(fair.is_active),
        industries=fair.industries,
        status=_public_status(fair, now),
        is_online=_public_is_online(fair),
        company_count=int(company_count or 0),
        candidate_count=int(candidate_count or 0),
        company_logos=logos,
        event_profile=_public_profile(fair),
    )


async def list_public_job_fairs_catalog(
    db: AsyncSession, *, search: Optional[str] = None
) -> JobFairPublicCatalogResponse:
    """Unauthenticated catalog split into live / upcoming / concluded."""
    now = datetime.utcnow()
    q = select(JobFair).where(JobFair.is_active.is_(True))

    if search and search.strip():
        term = f"%{search.strip()}%"
        company_match = select(JobFairCompany.job_fair_id).where(
            or_(
                JobFairCompany.company_name.ilike(term),
                exists().where(
                    and_(
                        User.id == JobFairCompany.provider_id,
                        User.company_name.ilike(term),
                    )
                ),
            )
        )
        q = q.where(
            or_(
                JobFair.title.ilike(term),
                JobFair.location.ilike(term),
                JobFair.description.ilike(term),
                JobFair.id.in_(company_match),
            )
        )

    q = q.order_by(JobFair.date.desc())
    fairs = (await db.execute(q)).scalars().all()
    fair_ids = [str(f.id) for f in fairs]

    company_counts: dict[str, int] = {}
    candidate_counts: dict[str, int] = {}
    if fair_ids:
        company_res = await db.execute(
            select(JobFairCompany.job_fair_id, func.count(JobFairCompany.id))
            .where(JobFairCompany.job_fair_id.in_(fair_ids))
            .group_by(JobFairCompany.job_fair_id)
        )
        company_counts = {str(fid): int(cnt) for fid, cnt in company_res.all()}

        seeker_res = await db.execute(
            select(JobFairSeeker.job_fair_id, func.count(JobFairSeeker.id))
            .where(JobFairSeeker.job_fair_id.in_(fair_ids))
            .group_by(JobFairSeeker.job_fair_id)
        )
        candidate_counts = {str(fid): int(cnt) for fid, cnt in seeker_res.all()}

    logos_map = await _company_logos_by_fair(db, fair_ids)

    live: list[JobFairPublicOut] = []
    upcoming: list[JobFairPublicOut] = []
    concluded: list[JobFairPublicOut] = []

    for fair in fairs:
        # Exclude draft events from website
        if _profile_dict(fair).get("lifecycle") == "draft":
            continue
        fid = str(fair.id)
        item = await _to_public_out(
            fair,
            company_count=company_counts.get(fid, 0),
            candidate_count=candidate_counts.get(fid, 0),
            logos=logos_map.get(fid, []),
            now=now,
        )
        if item.status == "live":
            live.append(item)
        elif item.status == "upcoming":
            upcoming.append(item)
        elif item.status == "concluded":
            concluded.append(item)

    live.sort(key=lambda x: x.date)
    upcoming.sort(key=lambda x: x.date)
    concluded.sort(key=lambda x: x.date, reverse=True)

    return JobFairPublicCatalogResponse(
        live=live,
        upcoming=upcoming,
        concluded=concluded,
        total=len(live) + len(upcoming) + len(concluded),
    )


async def get_public_job_fair_db(
    db: AsyncSession, id_or_slug: str
) -> Optional[JobFairPublicOut]:
    existing = await get_job_fair_db(db, id_or_slug)
    if not existing or not getattr(existing, "is_active", True):
        return None
    if _profile_dict(existing).get("lifecycle") == "draft":
        return None
    now = datetime.utcnow()
    logos_map = await _company_logos_by_fair(db, [existing.id])
    company_count = (
        await db.execute(
            select(func.count(JobFairCompany.id)).where(JobFairCompany.job_fair_id == existing.id)
        )
    ).scalar() or 0
    candidate_count = (
        await db.execute(
            select(func.count(JobFairSeeker.id)).where(JobFairSeeker.job_fair_id == existing.id)
        )
    ).scalar() or 0
    return JobFairPublicOut(
        id=existing.id,
        slug=existing.slug,
        title=existing.title,
        description=existing.description,
        date=existing.date,
        location=existing.location,
        banner_image_url=existing.banner_image_url,
        is_active=existing.is_active,
        industries=existing.industries,
        status=_public_status(existing, now),
        is_online=_public_is_online(existing),
        company_count=int(company_count),
        candidate_count=int(candidate_count),
        company_logos=logos_map.get(existing.id, []),
        event_profile=_public_profile(existing),
    )


async def get_job_fair_db(db: AsyncSession, id_or_slug: str) -> Optional[JobFairOut]:
    import uuid
    
    try:
        uuid.UUID(id_or_slug)
        condition = or_(
            JobFair.id == id_or_slug,
            JobFair.slug == id_or_slug
        )
    except ValueError:
        condition = JobFair.slug == id_or_slug

    q = select(JobFair).where(condition).limit(1)
    
    res = await db.execute(q)
    fair = res.scalar_one_or_none()
    return JobFairOut.model_validate(fair) if fair else None


async def list_job_fairs_for_ids_db(db: AsyncSession, fair_ids: list[str]) -> list[JobFairOut]:
    if not fair_ids:
        return []
    q = select(JobFair).where(JobFair.id.in_(fair_ids)).order_by(JobFair.date.desc(), JobFair.created_at.desc())
    res = await db.execute(q)
    fairs = res.scalars().all()
    return [JobFairOut.model_validate(f) for f in fairs]


async def create_job_fair_db(
    db: AsyncSession,
    *,
    title: str,
    description: Optional[str],
    fair_date: datetime,
    location: str,
    is_active: bool,
    slug: str,
    banner_image_url: Optional[str] = None,
    industries: Optional[list[str]] = None,
    event_profile: Optional[dict] = None,
    created_by_id: Optional[str] = None,
) -> JobFairOut:
    # created_by_id is ignored since it is not defined in the JobFair model / DB schema
    fair = JobFair(
        title=title,
        description=description,
        date=fair_date,
        location=location,
        is_active=is_active,
        slug=slug,
        banner_image_url=banner_image_url,
        industries=industries,
        event_profile=event_profile,
    )
    db.add(fair)
    await db.commit()
    await db.refresh(fair)
    return JobFairOut.model_validate(fair)


async def update_job_fair_db(
    db: AsyncSession,
    fair_id: str,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    fair_date: Optional[datetime] = None,
    location: Optional[str] = None,
    is_active: Optional[bool] = None,
    slug: Optional[str] = None,
    banner_image_url: Optional[str] = None,
    industries: Optional[list[str]] = None,
    event_profile: Optional[dict] = None,
) -> Optional[JobFairOut]:
    fair = await db.get(JobFair, fair_id)
    if not fair:
        return None

    if title is not None:
        fair.title = title
    if description is not None:
        fair.description = description
    if fair_date is not None:
        fair.date = fair_date
    if location is not None:
        fair.location = location
    if is_active is not None:
        fair.is_active = is_active
    if slug is not None:
        fair.slug = slug
    if banner_image_url is not None:
        fair.banner_image_url = banner_image_url
    if industries is not None:
        fair.industries = industries
    if event_profile is not None:
        fair.event_profile = event_profile

    fair.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(fair)
    return JobFairOut.model_validate(fair)


async def set_job_fair_banner_db(
    db: AsyncSession, fair_id: str, banner_image_url: str
) -> Optional[JobFairOut]:
    return await update_job_fair_db(
        db, fair_id, banner_image_url=banner_image_url
    )


async def delete_job_fair_db(db: AsyncSession, fair_id: str) -> bool:
    fair = await db.get(JobFair, fair_id)
    if fair:
        await db.delete(fair)
        await db.commit()
        return True
    return False
