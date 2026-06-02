from datetime import datetime
from typing import List, Optional
from services.ai_jobcreation_service import (
    generate_job_descriptions,
    generate_job_skills,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from services.jobs_service import (
    deactivate_job_service,
    get_job_or_404,
    schedule_cleanup,
    update_job_service,
    activate_job_service,
    schedule_activation
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.job import JobPosting, JobType
from models.user import User
from schemas.jobs import (
    JobCreate,
    JobDescriptionOnlyResponse,
    JobDescriptionRequest,
    JobOut,
    JobSkillsResponse,
    JobTitleRequest,
    JobUpdate,
)
from services.auth_service import require_provider, require_verified
from services.seeker_matching_service import embed_and_store_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=201)
async def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    job_type = None
    if body.job_type:
        try:
            job_type = JobType(body.job_type)
        except ValueError:
            pass

    # Auto-fill location for company users
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
    await db.commit()
    await db.refresh(job)

    # Embed and find matching candidates in background
    async def _process_job(job_id: str):
        from database import AsyncSessionLocal
        from services.seeker_matching_service import (
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

                # Step 1: Generate and store embedding
                await embed_and_store_job(job_obj, s)
                logger.info(f"[JOB] Embedding complete for {job_id}")

                # Step 2: Find and store all matching registered candidates
                await proactive_match_job_to_candidates(job_id)
                logger.info(f"[JOB] Proactive matching (seekers) complete for {job_id}")

                # Step 3: Celery-driven external candidate matching
                from services.celery_tasks import run_external_matching_for_job
                run_external_matching_for_job.delay(job_id)
                logger.info(f"[JOB] External candidate matching queued via Celery for {job_id}")

            except Exception as e:
                logger.exception(
                    f"[JOB] Background processing failed for {job_id}: {e}"
                )

    background_tasks.add_task(_process_job, job.id)

    return JobOut.model_validate(job)


@router.get("", response_model=List[JobOut])
async def list_jobs(
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    from models.user import UserRole

   
    # Providers see only their own job postings
    if user.role == UserRole.provider:
        result = await db.execute(
            select(JobPosting)
            .where(JobPosting.provider_id == user.id)
            .order_by(JobPosting.created_at.desc())
        )
    # Seekers see all active job postings
    else:
        result = await db.execute(
            select(JobPosting)
            .where(JobPosting.is_active == True)  # noqa
            .order_by(JobPosting.created_at.desc())
            .limit(100)
        )
    jobs = result.scalars().all()
    return [JobOut.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)



@router.patch("/{job_id}", response_model=JobOut)
async def update_job_patch(
    job_id: str,
    body: JobUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()

    if not job or str(job.provider_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Job not found")

    content_changed = await update_job_service(job, body, background_tasks)

    await db.commit()
    await db.refresh(job)

    if content_changed and job.is_active:
        from services.seeker_matching_service import invalidate_job_matches

        background_tasks.add_task(invalidate_job_matches, job.id)

    return JobOut.model_validate(job)


@router.put("/{job_id}", response_model=JobOut)
async def update_job_put(
    job_id: str,
    body: JobUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    print(body)
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    print(result)
    job = result.scalar_one_or_none()
    print(job)

    if not job or str(job.provider_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Job not found")

    content_changed = await update_job_service(job, body, background_tasks)

    await db.commit()
    await db.refresh(job)

    if content_changed and job.is_active:
        from services.seeker_matching_service import invalidate_job_matches

        background_tasks.add_task(invalidate_job_matches, job.id)

    return JobOut.model_validate(job)



@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    job = await get_job_or_404(job_id, user, db)

    await deactivate_job_service(job)

    await db.commit()

    schedule_cleanup(background_tasks, job)


@router.patch("/{job_id}/deactivate", status_code=204)
async def deactivate_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    job = await get_job_or_404(job_id, user, db)

    await deactivate_job_service(job)

    await db.commit()

    schedule_cleanup(background_tasks, job)


@router.patch("/{job_id}/activate", status_code=204)
async def activate_job(
    job_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    job = await get_job_or_404(job_id, user, db)

    await activate_job_service(job)

    await db.commit()



@router.get("/stats")
async def get_job_stats(
    user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(JobPosting).where(JobPosting.provider_id == user.id)
    )
    jobs = result.scalars().all()
    active_count = sum(1 for j in jobs if j.is_active)
    total_count = len(jobs)
    return {"active_jobs": active_count, "total_jobs": total_count}


@router.post("/generate-description", response_model=JobDescriptionOnlyResponse)
async def generate_description(payload: JobDescriptionRequest):
    try:
        # Generate description using the AI service
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
            perks=payload.perks
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error generating description: {e}")
        raise HTTPException(status_code=500, detail="Something went wrong")


@router.post("/generate-skills", response_model=JobSkillsResponse)
async def generate_skills(payload: JobTitleRequest):
    try:
        return await generate_job_skills(
            payload.title, payload.exp_min, payload.exp_max
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        raise HTTPException(status_code=500, detail="Something went wrong")
