from datetime import datetime
from typing import List, Optional
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.jobs_portal.models.job import JobPosting, JobType
from app.shared.models.user import User
from app.modules.jobs_portal.schemas.jobs import (
    JobCreate,
    JobDescriptionOnlyResponse,
    JobDescriptionRequest,
    JobOut,
    JobSkillsResponse,
    JobTitleRequest,
    JobUpdate,
)
from app.modules.jobs_portal.services.ai_jobcreation_service import generate_job_descriptions, generate_job_skills
from app.modules.jobs_portal.services.job_scrappers import search_external_jobs_paginated, clear_job_search_cache

from app.modules.jobs_portal.services.jobs_service import (
    deactivate_job_service,
    get_job_or_404,
    schedule_cleanup,
    update_job_service,
    activate_job_service,
    schedule_activation,
)
from app.modules.jobs_portal.services.seeker_matching_service import embed_and_store_job
from app.shared.services.audit_service import log_audit_event



async def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> JobOut:
    job_type = None
    if body.job_type:
        try:
            job_type = JobType(body.job_type)
        except ValueError:
            pass

    location = body.location
    if not location and user.company_location:
        location = user.company_location

    post_count = 0
    if body.post_count:
        try:
            post_count = int(body.post_count)
        except (ValueError, TypeError):
            post_count = 0

    job = JobPosting(
        provider_id=user.id,
        title=body.title,
        description=body.description,
        required_skills=body.required_skills or [],
        experience_required=body.experience_required,
        job_type=job_type,
        salary_range=body.salary_range,
        industry=body.industry or user.industry,
        posted_by_name=body.posted_by_name or f"{user.first_name} {user.last_name}",
        location=location,
        post_count=post_count,
        ai_interview_enabled=body.ai_interview_enabled or False,
        selection_threshold=body.selection_threshold or 70,
        shift=body.shift,
        employment_type=body.employment_type,
        perks=body.perks or [],
    )
    db.add(job)
    await log_audit_event(
        db,
        user,
        action="CREATE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Created job posting: '{job.title}' ({job.location or 'Remote'})",
        changes={"title": job.title, "location": job.location, "job_type": str(job_type) if job_type else None},
    )
    await db.commit()
    await db.refresh(job)

    async def _process_job(job_id: str):
        from app.core.database import AsyncSessionLocal
        from app.modules.jobs_portal.services.seeker_matching_service import (
            embed_and_store_job,
            proactive_match_job_to_candidates,
        )
        import logging

        logger = logging.getLogger(__name__)

        async with AsyncSessionLocal() as s:
            try:
                job_obj = await s.get(JobPosting, job_id)
                if not job_obj:
                    return

                await embed_and_store_job(job_obj, s)
                logger.info(f"[JOB] Embedding complete for {job_id}")

                await proactive_match_job_to_candidates(job_id)
                logger.info(f"[JOB] Proactive matching (seekers) complete for {job_id}")

                from app.shared.services.celery_tasks import run_external_matching_for_job
                run_external_matching_for_job.delay(job_id)
                logger.info(f"[JOB] External candidate matching queued via Celery for {job_id}")

            except Exception as e:
                logger.exception(f"[JOB] Background processing failed for {job_id}: {e}")

    background_tasks.add_task(_process_job, job.id)
    return JobOut.model_validate(job)


async def list_jobs(
    user: User,
    db: AsyncSession,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    search: Optional[str] = None,
    job_type: Optional[str] = None,
    salary_range: Optional[str] = None,
    industry: Optional[str] = None,
):
    from app.shared.models.user import UserRole
    from app.modules.jobs_portal.models.job import JobType as ModelJobType
    from sqlalchemy import func, and_, or_

    if user.role == UserRole.provider:
        base_query = (
            select(JobPosting)
            .where(JobPosting.provider_id == user.id)
            .order_by(JobPosting.created_at.desc())
        )
    else:
        base_query = (
            select(JobPosting)
            .where(JobPosting.is_active == True)  # noqa
            .order_by(JobPosting.created_at.desc())
        )

    # Apply search and filters
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                JobPosting.title.ilike(term),
                JobPosting.description.ilike(term),
                JobPosting.location.ilike(term),
                JobPosting.posted_by_name.ilike(term),
            )
        )
    if job_type and job_type != "all":
        try:
            filters.append(JobPosting.job_type == ModelJobType(job_type))
        except ValueError:
            pass
    if salary_range and salary_range != "all":
        filters.append(JobPosting.salary_range.ilike(f"%{salary_range.strip()}%"))
    if industry and industry != "all":
        filters.append(func.lower(JobPosting.industry) == industry.strip().lower())

    if filters:
        base_query = base_query.where(and_(*filters))

    if page is not None and page_size is not None:
        count_query = select(func.count(JobPosting.id)).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        offset = (page - 1) * page_size
        query = base_query.offset(offset).limit(page_size)
        result = await db.execute(query)
        jobs = result.scalars().all()

        return {
            "items": [JobOut.model_validate(j) for j in jobs],
            "total": int(total),
            "page": page,
            "page_size": page_size,
        }
    else:
        if user.role != UserRole.provider:
            base_query = base_query.limit(100)
        result = await db.execute(base_query)
        jobs = result.scalars().all()
        return [JobOut.model_validate(j) for j in jobs]


async def get_distinct_industries(db: AsyncSession) -> List[str]:
    from sqlalchemy import distinct
    query = (
        select(distinct(JobPosting.industry))
        .where(JobPosting.industry.isnot(None), JobPosting.industry != "")
        .order_by(JobPosting.industry)
    )
    result = await db.execute(query)
    industries = [r for r in result.scalars().all() if r and r.strip()]
    return industries


async def get_job(job_id: str, user: User, db: AsyncSession) -> JobOut:
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


async def update_job_patch(
    job_id: str,
    body: JobUpdate,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> JobOut:
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()

    if not job or str(job.provider_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Job not found")

    content_changed = await update_job_service(job, body, background_tasks)
    await db.commit()
    await db.refresh(job)

    if content_changed and job.is_active:
        from app.modules.jobs_portal.services.seeker_matching_service import invalidate_job_matches
        background_tasks.add_task(invalidate_job_matches, job.id)

    return JobOut.model_validate(job)


async def update_job_put(
    job_id: str,
    body: JobUpdate,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> JobOut:
    print(body)
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    print(result)
    job = result.scalar_one_or_none()
    print(job)

    if not job or str(job.provider_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Job not found")

    content_changed = await update_job_service(job, body, background_tasks)
    await log_audit_event(
        db,
        user,
        action="UPDATE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Updated job posting: '{job.title}'",
    )
    await db.commit()
    await db.refresh(job)

    if content_changed and job.is_active:
        from app.modules.jobs_portal.services.seeker_matching_service import invalidate_job_matches
        background_tasks.add_task(invalidate_job_matches, job.id)

    return JobOut.model_validate(job)


async def delete_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> None:
    job = await get_job_or_404(job_id, user, db)
    # Hard delete — cascades to applications and matches via DB relationship
    await log_audit_event(
        db,
        user,
        action="DELETE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Deleted job posting: '{job.title}'",
    )
    await db.delete(job)
    await db.commit()


async def deactivate_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> None:
    job = await get_job_or_404(job_id, user, db)
    await deactivate_job_service(job)
    await log_audit_event(
        db,
        user,
        action="STATUS_CHANGE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Deactivated job posting: '{job.title}'",
        changes={"is_active": False},
    )
    await db.commit()
    schedule_cleanup(background_tasks, job)


async def activate_job(job_id: str, user: User, db: AsyncSession) -> None:
    job = await get_job_or_404(job_id, user, db)
    await activate_job_service(job)
    await log_audit_event(
        db,
        user,
        action="STATUS_CHANGE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=f"Activated job posting: '{job.title}'",
        changes={"is_active": True},
    )
    await db.commit()


async def get_job_stats(user: User, db: AsyncSession) -> dict:
    result = await db.execute(
        select(JobPosting).where(JobPosting.provider_id == user.id)
    )
    jobs = result.scalars().all()
    active_count = sum(1 for j in jobs if j.is_active)
    total_count = len(jobs)
    return {"active_jobs": active_count, "total_jobs": total_count}


async def generate_description(payload: JobDescriptionRequest) -> JobDescriptionOnlyResponse:
    try:
        result = await generate_job_descriptions(
            title=payload.title,
            exp_min=payload.exp_min,
            exp_max=payload.exp_max,
            sal_min=payload.sal_min,
            sal_max=payload.sal_max,
            salary_range=payload.salary_range,
            location=payload.location,
            job_type=payload.job_type,
            employment_type=payload.employment_type,
            shift=payload.shift,
            required_skills=payload.required_skills,
            perks=payload.perks,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error generating description: {e}")
        raise HTTPException(status_code=500, detail="Something went wrong")


async def generate_skills(payload: JobTitleRequest) -> JobSkillsResponse:
    try:
        return await generate_job_skills(payload.title, payload.exp_min, payload.exp_max)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Something went wrong")


async def search_external_jobs(
    query: str,
    location: str = "",
    page: int = 1,
    page_size: int = 20,
    greenhouse_board: str = "",
    force_refresh: bool = False
) -> dict:
    """
    Controller method for parallel, async paginated job search across external portals (Apna.co, Foundit.in, & Greenhouse.io).
    """
    from app.modules.jobs_portal.services.job_scrappers import search_external_jobs_paginated
    return await search_external_jobs_paginated(
        query=query,
        location=location or "",
        page=page,
        page_size=page_size,
        greenhouse_board=greenhouse_board or "",
        force_refresh=force_refresh
    )




async def clear_external_jobs_cache():
    """
    Controller method to flush job search cache from Redis.
    """
    from app.modules.jobs_portal.services.job_scrappers import clear_job_search_cache
    count = await clear_job_search_cache()
    return {"message": f"Successfully cleared {count} cached search entries from Redis.", "cleared_count": count}


