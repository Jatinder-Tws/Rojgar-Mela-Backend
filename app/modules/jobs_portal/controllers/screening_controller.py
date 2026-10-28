"""HTTP-facing controllers for AI Resume Screening."""

from __future__ import annotations

from typing import List, Optional

from fastapi import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.schemas.screening import (
    BulkDecisionIn,
    RecruiterDecisionIn,
    ReportCreateIn,
    ScreeningBatchCreate,
)
from app.modules.jobs_portal.services import screening_service as svc
from app.shared.models.user import User


async def create_batch(payload: ScreeningBatchCreate, user: User, db: AsyncSession):
    return await svc.create_batch(payload, user, db)


async def list_batches(
    user: User,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    has_pending_review: Optional[bool] = None,
    has_failed_files: Optional[bool] = None,
):
    return await svc.list_batches(
        user,
        db,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        has_pending_review=has_pending_review,
        has_failed_files=has_failed_files,
    )


async def delete_batch(batch_id: str, user: User, db: AsyncSession):
    return await svc.delete_batch(batch_id, user, db)


async def get_batch(batch_id: str, user: User, db: AsyncSession):
    return await svc.get_batch_detail(batch_id, user, db)


async def get_limits(user: User, db: AsyncSession):
    return await svc.get_limits(user, db)


async def upload(batch_id: str, files: List[UploadFile], user: User, db: AsyncSession):
    return await svc.upload_resumes(batch_id, files, user, db)


async def remove_file(batch_id: str, resume_id: str, user: User, db: AsyncSession):
    return await svc.remove_resume(batch_id, resume_id, user, db)


async def start(batch_id: str, user: User, db: AsyncSession):
    return await svc.start_processing(batch_id, user, db)


async def progress(batch_id: str, user: User, db: AsyncSession):
    return await svc.get_progress(batch_id, user, db)


async def cancel(batch_id: str, user: User, db: AsyncSession):
    return await svc.cancel_batch(batch_id, user, db)


async def retry(batch_id: str, user: User, db: AsyncSession):
    return await svc.retry_failed(batch_id, user, db)


async def results(
    batch_id: str,
    user: User,
    db: AsyncSession,
    jd_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    search: Optional[str] = None,
    min_score: Optional[float] = None,
    decision: Optional[str] = None,
    quality_status: Optional[str] = None,
    sort: str = "score_desc",
):
    return await svc.list_results(
        batch_id, user, db,
        jd_id=jd_id, page=page, page_size=page_size,
        search=search, min_score=min_score, decision=decision,
        quality_status=quality_status, sort=sort,
    )


async def candidate(batch_id: str, match_id: str, user: User, db: AsyncSession):
    return await svc.get_candidate_detail(batch_id, match_id, user, db)


async def decide(batch_id: str, match_id: str, payload: RecruiterDecisionIn, user: User, db: AsyncSession):
    return await svc.update_decision(batch_id, match_id, payload, user, db)


async def bulk_decide(batch_id: str, payload: BulkDecisionIn, user: User, db: AsyncSession):
    return await svc.bulk_decision(batch_id, payload, user, db)


async def create_report(batch_id: str, payload: ReportCreateIn, user: User, db: AsyncSession):
    return await svc.create_report(batch_id, payload, user, db)


async def list_reports(batch_id: str, user: User, db: AsyncSession):
    return await svc.list_reports(batch_id, user, db)


async def download_report(batch_id: str, report_id: str, user: User, db: AsyncSession):
    path, media, name = await svc.get_report_file(batch_id, report_id, user, db)
    return FileResponse(path, media_type=media, filename=name)


async def download_resume(batch_id: str, resume_id: str, user: User, db: AsyncSession):
    path, name = await svc.get_resume_file(batch_id, resume_id, user, db)
    return FileResponse(path, filename=name)
