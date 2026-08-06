from typing import Optional, Union
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession


from database import get_db
from models.user import User
from schemas.jobs import (
    JobCreate, JobDescriptionOnlyResponse, JobDescriptionRequest,
    JobOut, JobSkillsResponse, JobTitleRequest, JobUpdate,
    JobListResponse,
)
from services.auth_service import require_provider, require_verified
from controllers.jobs_controller import (
    list_jobs as ctrl_list_jobs,
    create_job as ctrl_create_job,
    get_job as ctrl_get_job,
    update_job_patch as ctrl_update_job_patch,
    update_job_put as ctrl_update_job_put,
    delete_job as ctrl_delete_job,
    deactivate_job as ctrl_deactivate_job,
    activate_job as ctrl_activate_job,
    get_job_stats as ctrl_get_job_stats,
    generate_description as ctrl_generate_description,
    generate_skills as ctrl_generate_skills,
    get_distinct_industries as ctrl_get_distinct_industries,
    search_external_jobs as ctrl_search_external_jobs,
    clear_external_jobs_cache as ctrl_clear_external_jobs_cache,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])



@router.post("", response_model=JobOut, status_code=201)
async def create_job(body: JobCreate, background_tasks: BackgroundTasks, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_create_job(body, background_tasks, user, db)


@router.get("", response_model=Union[JobListResponse, list[JobOut]])
async def list_jobs(
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    search: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    salary_range: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    return await ctrl_list_jobs(
        user, db, page, page_size, search, job_type, salary_range, industry
    )


@router.get("/stats")
async def get_job_stats(user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_job_stats(user, db)


@router.get("/industries", response_model=list[str])
async def get_distinct_industries(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_distinct_industries(db)


@router.get("/external-search")
async def search_external_jobs(
    query: str = Query(..., description="Job title or search keyword"),
    location: Optional[str] = Query("", description="Job location filter"),
    page: int = Query(1, ge=1, description="Page number (default 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (default 20, max 100)"),
    greenhouse_board: Optional[str] = Query("", description="Optional Greenhouse board token (e.g. github, stripe, cloudflare, postman)"),
    force_refresh: bool = Query(False, description="Bypass Redis cache"),
):
    """
    Public async paginated job search endpoint for Apna.co, Foundit.in, and Greenhouse.io portals (No Authentication Required).
    Returns normalized job results from all portals using concurrent parallel API execution.
    Supports pagination parameters (page, page_size) and optional Greenhouse board filtering.
    """
    return await ctrl_search_external_jobs(
        query=query,
        location=location or "",
        page=page,
        page_size=page_size,
        greenhouse_board=greenhouse_board or "",
        force_refresh=force_refresh
    )




@router.post("/clear-external-cache")
@router.delete("/clear-external-cache")
async def clear_external_cache():
    """
    Clear all external job search entries from Redis cache.
    """
    return await ctrl_clear_external_jobs_cache()



@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_job(job_id, user, db)



@router.patch("/{job_id}", response_model=JobOut)
async def update_job_patch(job_id: str, body: JobUpdate, background_tasks: BackgroundTasks, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_job_patch(job_id, body, background_tasks, user, db)


@router.put("/{job_id}", response_model=JobOut)
async def update_job_put(job_id: str, body: JobUpdate, background_tasks: BackgroundTasks, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_job_put(job_id, body, background_tasks, user, db)


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str, background_tasks: BackgroundTasks, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_delete_job(job_id, background_tasks, user, db)


@router.patch("/{job_id}/deactivate", status_code=204)
async def deactivate_job(job_id: str, background_tasks: BackgroundTasks, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_deactivate_job(job_id, background_tasks, user, db)


@router.patch("/{job_id}/activate", status_code=204)
async def activate_job(job_id: str, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_activate_job(job_id, user, db)


@router.post("/ai/generate-description", response_model=JobDescriptionOnlyResponse)
async def generate_description(payload: JobDescriptionRequest, user: User = Depends(require_provider)):
    return await ctrl_generate_description(payload)


@router.post("/ai/generate-skills", response_model=JobSkillsResponse)
async def generate_skills(payload: JobTitleRequest, user: User = Depends(require_provider)):
    return await ctrl_generate_skills(payload)





