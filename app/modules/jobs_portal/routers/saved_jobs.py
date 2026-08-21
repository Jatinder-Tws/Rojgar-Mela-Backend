from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.modules.jobs_portal.models.job import JobPosting
from app.modules.jobs_portal.models.saved_job import SavedJob
from app.shared.models.user import User
from app.core.dependencies import require_seeker
from app.modules.jobs_portal.services.public_jobs_service import serialize_public_job

router = APIRouter(prefix="/saved-jobs", tags=["saved-jobs"])


class SavedJobIdsOut(BaseModel):
    job_ids: List[str]


class SavedJobToggleOut(BaseModel):
    job_id: str
    saved: bool


@router.get("/ids", response_model=SavedJobIdsOut)
async def list_saved_job_ids(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob.job_id).filter(SavedJob.seeker_id == user.id)
    )
    return SavedJobIdsOut(job_ids=[str(row[0]) for row in result.all()])


@router.get("")
async def list_saved_jobs(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob)
        .options(selectinload(SavedJob.job).selectinload(JobPosting.provider))
        .filter(SavedJob.seeker_id == user.id)
        .order_by(SavedJob.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        serialize_public_job(row.job)
        for row in rows
        if row.job is not None and row.job.is_active
    ]


@router.post("/{job_id}", response_model=SavedJobToggleOut, status_code=201)
async def save_job(
    job_id: str,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(JobPosting, job_id)
    if not job or not job.is_active:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = await db.execute(
        select(SavedJob).filter(
            SavedJob.seeker_id == user.id,
            SavedJob.job_id == job_id,
        )
    )
    if existing.scalar_one_or_none():
        return SavedJobToggleOut(job_id=job_id, saved=True)

    db.add(SavedJob(seeker_id=user.id, job_id=job_id))
    await db.commit()
    return SavedJobToggleOut(job_id=job_id, saved=True)


@router.delete("/{job_id}", response_model=SavedJobToggleOut)
async def unsave_job(
    job_id: str,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob).filter(
            SavedJob.seeker_id == user.id,
            SavedJob.job_id == job_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return SavedJobToggleOut(job_id=job_id, saved=False)
