"""
ORM-based database helpers for job_fairs table.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.job_fair import JobFair
from schemas.job_fair import JobFairOut


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
