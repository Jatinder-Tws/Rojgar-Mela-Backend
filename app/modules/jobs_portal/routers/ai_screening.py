"""Provider AI Resume Screening API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_provider
from app.modules.jobs_portal.controllers import screening_controller as ctrl
from app.modules.jobs_portal.schemas.screening import (
    BulkDecisionIn,
    RecruiterDecisionIn,
    ReportCreateIn,
    ReportOut,
    ScreeningBatchCreate,
    ScreeningBatchDetail,
    ScreeningBatchListOut,
    ScreeningLimitsOut,
    ScreeningProgressOut,
    ScreeningUploadResponse,
    MatchResultsPage,
    MatchResultOut,
)
from app.shared.models.user import User

router = APIRouter(prefix="/ai-screening", tags=["ai-screening"])


@router.get("/limits", response_model=ScreeningLimitsOut)
async def get_limits(
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.get_limits(user, db)


@router.get("/batches", response_model=ScreeningBatchListOut)
async def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    has_pending_review: Optional[bool] = Query(None),
    has_failed_files: Optional[bool] = Query(None),
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.list_batches(
        user,
        db,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        has_pending_review=has_pending_review,
        has_failed_files=has_failed_files,
    )


@router.delete("/batches/{batch_id}")
async def delete_batch(
    batch_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.delete_batch(batch_id, user, db)


@router.post("/batches", response_model=ScreeningBatchDetail)
async def create_batch(
    payload: ScreeningBatchCreate,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.create_batch(payload, user, db)


@router.get("/batches/{batch_id}", response_model=ScreeningBatchDetail)
async def get_batch(
    batch_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.get_batch(batch_id, user, db)


@router.post("/batches/{batch_id}/uploads", response_model=ScreeningUploadResponse)
async def upload_resumes(
    batch_id: str,
    files: List[UploadFile] = File(...),
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.upload(batch_id, files, user, db)


@router.delete("/batches/{batch_id}/resumes/{resume_id}", response_model=ScreeningBatchDetail)
async def remove_resume(
    batch_id: str,
    resume_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.remove_file(batch_id, resume_id, user, db)


@router.post("/batches/{batch_id}/start", response_model=ScreeningProgressOut)
async def start_processing(
    batch_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.start(batch_id, user, db)


@router.get("/batches/{batch_id}/progress", response_model=ScreeningProgressOut)
async def get_progress(
    batch_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.progress(batch_id, user, db)


@router.post("/batches/{batch_id}/cancel", response_model=ScreeningProgressOut)
async def cancel_batch(
    batch_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.cancel(batch_id, user, db)


@router.post("/batches/{batch_id}/retry-failed", response_model=ScreeningProgressOut)
async def retry_failed(
    batch_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.retry(batch_id, user, db)


@router.get("/batches/{batch_id}/results", response_model=MatchResultsPage)
async def get_results(
    batch_id: str,
    jd_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    decision: Optional[str] = Query(None),
    quality_status: Optional[str] = Query(None),
    sort: str = Query("score_desc"),
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.results(
        batch_id, user, db,
        jd_id=jd_id, page=page, page_size=page_size,
        search=search, min_score=min_score, decision=decision,
        quality_status=quality_status, sort=sort,
    )


@router.get("/batches/{batch_id}/candidates/{match_id}")
async def get_candidate(
    batch_id: str,
    match_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.candidate(batch_id, match_id, user, db)


@router.patch("/batches/{batch_id}/candidates/{match_id}/decision", response_model=MatchResultOut)
async def update_decision(
    batch_id: str,
    match_id: str,
    payload: RecruiterDecisionIn,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.decide(batch_id, match_id, payload, user, db)


@router.post("/batches/{batch_id}/decisions/bulk")
async def bulk_decisions(
    batch_id: str,
    payload: BulkDecisionIn,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.bulk_decide(batch_id, payload, user, db)


@router.post("/batches/{batch_id}/reports", response_model=ReportOut)
async def create_report(
    batch_id: str,
    payload: ReportCreateIn,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.create_report(batch_id, payload, user, db)


@router.get("/batches/{batch_id}/reports", response_model=List[ReportOut])
async def list_reports(
    batch_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.list_reports(batch_id, user, db)


@router.get("/batches/{batch_id}/reports/{report_id}/download")
async def download_report(
    batch_id: str,
    report_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.download_report(batch_id, report_id, user, db)


@router.get("/batches/{batch_id}/resumes/{resume_id}/download")
async def download_resume(
    batch_id: str,
    resume_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.download_resume(batch_id, resume_id, user, db)
