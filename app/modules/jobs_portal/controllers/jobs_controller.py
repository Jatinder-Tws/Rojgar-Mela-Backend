from datetime import datetime
from typing import List, Optional
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.modules.jobs_portal.models.job import JobPosting, JobType
from app.shared.models.user import User
from app.modules.jobs_portal.schemas.jobs import (
    ApplyInsightsRequest,
    ApplyInsightsResponse,
    ApplyInsightWarningOut,
    EnhanceJobSectionRequest,
    EnhanceJobSectionResponse,
    JobCreate,
    JobDescriptionOnlyResponse,
    JobDescriptionRequest,
    JobOut,
    JobSkillsResponse,
    JobTitleRequest,
    JobUpdate,
    VoiceJobParseRequest,
    VoiceJobParseResponse,
)
from app.modules.jobs_portal.services.ai_jobcreation_service import (
    enhance_job_section,
    generate_job_descriptions,
    generate_job_skills,
    parse_spoken_job,
)
from app.modules.jobs_portal.services.job_scrappers import search_external_jobs_paginated, clear_job_search_cache

from app.modules.jobs_portal.services.jobs_service import (
    deactivate_job_service,
    get_job_or_404,
    schedule_cleanup,
    update_job_service,
    activate_job_service,
    schedule_activation,
    apply_posting_details,
)
from app.modules.jobs_portal.services.seeker_matching_service import embed_and_store_job
from app.shared.services.audit_service import log_audit_event



def _queue_job_processing(background_tasks: BackgroundTasks, job_id: str) -> None:
    async def _process_job(target_id: str):
        from app.core.database import AsyncSessionLocal
        from app.modules.jobs_portal.services.seeker_matching_service import (
            embed_and_store_job,
            proactive_match_job_to_candidates,
        )
        import logging

        logger = logging.getLogger(__name__)

        async with AsyncSessionLocal() as session:
            try:
                job_obj = await session.get(JobPosting, target_id)
                if not job_obj:
                    return

                await embed_and_store_job(job_obj, session)
                logger.info(f"[JOB] Embedding complete for {target_id}")

                await proactive_match_job_to_candidates(target_id)
                logger.info(f"[JOB] Proactive matching (seekers) complete for {target_id}")

                from app.shared.services.celery_tasks import run_external_matching_for_job
                run_external_matching_for_job.delay(target_id)
                logger.info(f"[JOB] External candidate matching queued via Celery for {target_id}")
            except Exception as exc:
                logger.exception(f"[JOB] Background processing failed for {target_id}: {exc}")

    background_tasks.add_task(_process_job, job_id)


async def create_job_for_provider(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    provider: User,
    actor: User,
    db: AsyncSession,
    *,
    audit_description: Optional[str] = None,
) -> JobOut:
    """Create a job owned by ``provider``; ``actor`` is recorded on the audit log."""
    job_type = None
    if body.job_type:
        try:
            job_type = JobType(body.job_type)
        except ValueError:
            pass

    location = body.location
    if not location and provider.company_location:
        location = provider.company_location

    post_count = 0
    if body.post_count:
        try:
            post_count = int(body.post_count)
        except (ValueError, TypeError):
            post_count = 0

    company_label = (
        provider.company_name
        or f"{(provider.first_name or '').strip()} {(provider.last_name or '').strip()}".strip()
        or "Provider"
    )
    job = JobPosting(
        provider_id=provider.id,
        title=body.title,
        description=body.description,
        required_skills=body.required_skills or [],
        experience_required=body.experience_required,
        job_type=job_type,
        salary_range=body.salary_range,
        industry=body.industry or provider.industry,
        posted_by_name=body.posted_by_name or company_label,
        location=location,
        post_count=post_count,
        ai_interview_enabled=body.ai_interview_enabled or False,
        selection_threshold=body.selection_threshold or 70,
        shift=body.shift,
        employment_type=body.employment_type,
        perks=body.perks or [],
        is_active=True if body.is_active is None else bool(body.is_active),
    )
    apply_posting_details(job, body.posting_details)
    db.add(job)
    await log_audit_event(
        db,
        actor,
        action="CREATE",
        entity_type="job",
        entity_id=str(job.id),
        entity_name=job.title,
        description=audit_description
        or f"Created job posting: '{job.title}' ({job.location or 'Remote'})",
        changes={
            "title": job.title,
            "location": job.location,
            "job_type": str(job_type) if job_type else None,
            "provider_id": str(provider.id),
        },
    )
    await db.commit()
    await db.refresh(job)

    if job.is_active:
        _queue_job_processing(background_tasks, job.id)
    return JobOut.model_validate(job)


async def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    user: User,
    db: AsyncSession,
) -> JobOut:
    return await create_job_for_provider(body, background_tasks, user, user, db)


JOB_SORTABLE_COLUMNS = {
    "title": JobPosting.title,
    "posted_by_name": JobPosting.posted_by_name,
    "location": JobPosting.location,
    "job_type": JobPosting.job_type,
    "created_at": JobPosting.created_at,
}

# Minimum AI match score to treat a job as "matched" in browse filters/badges.
MATCHED_SCORE_FLOOR = 40.0


async def _provider_company_fields_by_id(
    db: AsyncSession,
    provider_ids: list[str],
) -> dict[str, dict]:
    """Map provider id -> company_logo_url / company_name for list enrichment."""
    if not provider_ids:
        return {}
    result = await db.execute(
        select(User.id, User.profile_pic_url, User.company_name).where(User.id.in_(provider_ids))
    )
    out: dict[str, dict] = {}
    for row in result.all():
        out[str(row.id)] = {
            "company_logo_url": row.profile_pic_url,
            "company_name": row.company_name,
        }
    return out


async def _enrich_jobs_with_seeker_matches(
    db: AsyncSession,
    user: User,
    jobs: list,
) -> list[JobOut]:
    """Attach Match score/highlights/gaps and provider logo/name onto JobOut rows."""
    from app.shared.models.user import UserRole
    from app.modules.jobs_portal.models.match import Match

    if not jobs:
        return []

    provider_fields = await _provider_company_fields_by_id(
        db,
        list({str(j.provider_id) for j in jobs if getattr(j, "provider_id", None)}),
    )

    by_job: dict = {}
    if user.role == UserRole.seeker:
        job_ids = [j.id for j in jobs]
        match_result = await db.execute(
            select(Match).where(Match.seeker_id == user.id, Match.job_id.in_(job_ids))
        )
        by_job = {str(m.job_id): m for m in match_result.scalars().all()}

    enriched: list[JobOut] = []
    for job in jobs:
        payload = JobOut.model_validate(job).model_dump()
        company = provider_fields.get(str(job.provider_id)) or {}
        if company.get("company_logo_url"):
            payload["company_logo_url"] = company["company_logo_url"]
        if company.get("company_name") and not payload.get("company_name"):
            payload["company_name"] = company["company_name"]
        match = by_job.get(str(job.id))
        if match:
            payload["match_score"] = match.score
            payload["fit_reason"] = match.fit_reason
            payload["highlights"] = match.highlights or []
            payload["gaps"] = match.gaps or []
        enriched.append(JobOut.model_validate(payload))
    return enriched


async def list_jobs(
    user: User,
    db: AsyncSession,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    search: Optional[str] = None,
    job_type: Optional[str] = None,
    salary_range: Optional[str] = None,
    industry: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    matched_only: bool = False,
):
    from app.shared.models.user import UserRole
    from app.modules.jobs_portal.models.job import JobType as ModelJobType
    from app.modules.jobs_portal.models.match import Match
    from sqlalchemy import func, and_, or_

    sort_key = sort_by or "created_at"
    sort_by_match = sort_key == "match_score" and user.role == UserRole.seeker
    use_match_join = (matched_only or sort_by_match) and user.role == UserRole.seeker

    if user.role == UserRole.provider:
        base_query = select(JobPosting).where(JobPosting.provider_id == user.id)
    else:
        base_query = select(JobPosting).where(JobPosting.is_active == True)  # noqa

    if use_match_join:
        join_on = and_(Match.job_id == JobPosting.id, Match.seeker_id == user.id)
        if matched_only:
            base_query = base_query.join(Match, join_on).where(Match.score >= MATCHED_SCORE_FLOOR)
        else:
            base_query = base_query.outerjoin(Match, join_on)

    if sort_by_match:
        order_fn = Match.score.asc().nullsfirst() if sort_order == "asc" else Match.score.desc().nullslast()
        # Stable tie-breaker so pages do not shuffle.
        base_query = base_query.order_by(order_fn, JobPosting.created_at.desc())
    else:
        sort_column = JOB_SORTABLE_COLUMNS.get(sort_key, JobPosting.created_at)
        order_fn = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        base_query = base_query.order_by(order_fn)

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
        # Count job rows only. Counting JobPosting.id against the entity
        # subquery cross-joins the table and inflates the total (vacancy-sized).
        count_query = select(func.count()).select_from(base_query.order_by(None).subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        offset = (page - 1) * page_size
        query = base_query.offset(offset).limit(page_size)
        result = await db.execute(query)
        jobs = result.scalars().unique().all()

        return {
            "items": await _enrich_jobs_with_seeker_matches(db, user, jobs),
            "total": int(total),
            "page": page,
            "page_size": page_size,
        }
    else:
        if user.role != UserRole.provider:
            base_query = base_query.limit(100)
        result = await db.execute(base_query)
        jobs = result.scalars().unique().all()
        return await _enrich_jobs_with_seeker_matches(db, user, jobs)


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
    result = await db.execute(
        select(JobPosting)
        .options(selectinload(JobPosting.provider).selectinload(User.company_gallery_images))
        .where(JobPosting.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    from app.modules.jobs_portal.services.company_profile_service import public_company_payload

    payload = JobOut.model_validate(job).model_dump()
    payload.update(public_company_payload(job.provider))
    enriched = await _enrich_jobs_with_seeker_matches(db, user, [job])
    if enriched:
        merged = enriched[0].model_dump()
        # Keep company profile fields from public_company_payload.
        for key, value in payload.items():
            if key not in ("match_score", "fit_reason", "highlights", "gaps"):
                merged[key] = value
        return JobOut.model_validate(merged)
    return JobOut.model_validate(payload)


async def apply_insights(
    job_id: str,
    body: ApplyInsightsRequest,
    user: User,
    db: AsyncSession,
) -> ApplyInsightsResponse:
    """Polish apply soft-warnings with AI when available; otherwise return heuristics unchanged."""
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.modules.jobs_portal.services.apply_insights_service import polish_apply_warnings

    required = job.required_skills if isinstance(job.required_skills, list) else []
    polished, source = await polish_apply_warnings(
        job_title=job.title or "this role",
        job_description=job.description,
        job_salary=job.salary_range,
        required_skills=[str(s) for s in required if s],
        seeker_job_role=body.seeker_job_role or getattr(user, "job_role", None),
        seeker_industry=body.seeker_industry or getattr(user, "industry", None),
        seeker_skills=body.seeker_skills or [],
        expected_salary=body.expected_salary or getattr(user, "salary_range", None),
        warnings=[w.model_dump() for w in (body.warnings or [])],
    )
    return ApplyInsightsResponse(
        warnings=[ApplyInsightWarningOut.model_validate(w) for w in polished],
        source=source,
    )


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

    was_active = bool(job.is_active)
    content_changed = await update_job_service(job, body, background_tasks)
    await db.commit()
    await db.refresh(job)

    if job.is_active and not was_active:
        _queue_job_processing(background_tasks, str(job.id))
    elif content_changed and job.is_active:
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

    was_active = bool(job.is_active)
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

    if job.is_active and not was_active:
        _queue_job_processing(background_tasks, str(job.id))
    elif content_changed and job.is_active:
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


async def parse_voice_job(payload: VoiceJobParseRequest) -> VoiceJobParseResponse:
    try:
        result = await parse_spoken_job(payload.transcript, payload.audio_base64, payload.audio_mime)
        return VoiceJobParseResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Error parsing spoken job: {exc}")
        raise HTTPException(status_code=500, detail="Could not understand that recording. Please try again.") from exc


async def generate_skills(payload: JobTitleRequest) -> JobSkillsResponse:
    try:
        return await generate_job_skills(payload.title, payload.exp_min, payload.exp_max)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Something went wrong")


async def enhance_section(payload: EnhanceJobSectionRequest) -> EnhanceJobSectionResponse:
    try:
        result = await enhance_job_section(
            section=payload.section,
            title=payload.title,
            current_text=payload.current_text,
            location=payload.location,
            job_type=payload.job_type,
            employment_type=payload.employment_type,
            experience=payload.experience,
            required_skills=payload.required_skills or [],
        )
        return EnhanceJobSectionResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error enhancing job section: {e}")
        raise HTTPException(status_code=500, detail="Could not enhance this section")


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


