from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.jobs import (
    JobCreate, JobDescriptionOnlyResponse, JobDescriptionRequest,
    JobOut, JobSkillsResponse, JobTitleRequest, JobUpdate,
)
from services.auth_service import require_provider, require_verified
from controllers.jobs_controller import (
    create_job as ctrl_create_job,
    list_jobs as ctrl_list_jobs,
    get_job as ctrl_get_job,
    update_job_patch as ctrl_update_job_patch,
    update_job_put as ctrl_update_job_put,
    delete_job as ctrl_delete_job,
    deactivate_job as ctrl_deactivate_job,
    activate_job as ctrl_activate_job,
    get_job_stats as ctrl_get_job_stats,
    generate_description as ctrl_generate_description,
    generate_skills as ctrl_generate_skills,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=201)
async def create_job(body: JobCreate, background_tasks: BackgroundTasks, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_create_job(body, background_tasks, user, db)


@router.get("", response_model=list[JobOut])
async def list_jobs(user: User = Depends(require_verified), db: AsyncSession = Depends(get_db)):
    return await ctrl_list_jobs(user, db)


@router.get("/stats")
async def get_job_stats(user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_job_stats(user, db)


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
