"""Business logic for provider AI Resume Screening batches."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Sequence, Tuple

from fastapi import HTTPException, UploadFile
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.jobs_portal.models.job import JobPosting
from app.modules.jobs_portal.models.screening import (
    ScreeningBatch,
    ScreeningBatchResume,
    ScreeningCandidateMatch,
    ScreeningJD,
    ScreeningReport,
    ScreeningResumeProfile,
    ScreeningTaskEvent,
)
from app.modules.jobs_portal.schemas.screening import (
    BulkDecisionIn,
    ManualJDIn,
    MatchResultOut,
    MatchResultsPage,
    RecruiterDecisionIn,
    ReportCreateIn,
    ReportOut,
    ScreeningBatchCreate,
    ScreeningBatchDetail,
    ScreeningBatchListOut,
    ScreeningBatchSummary,
    ScreeningDashboardStats,
    ScreeningFailedFileOut,
    ScreeningJDOut,
    ScreeningLimitsOut,
    ScreeningProgressOut,
    ScreeningUploadResponse,
    ScreeningUploadResult,
)
from app.modules.jobs_portal.services.screening_skills import normalize_skills, parse_experience_years
from app.modules.jobs_portal.services.screening_storage import (
    SCREENING_ALLOWED_EXT,
    delete_provider_batch_dir,
    delete_storage_key,
    resolve_storage_path,
    save_screening_upload,
)
from app.shared.models.user import User

logger = logging.getLogger(__name__)


def _limits_snapshot() -> dict:
    return {
        "max_resumes_per_batch": settings.SCREENING_MAX_RESUMES_PER_BATCH,
        "max_concurrent_batches": settings.SCREENING_MAX_CONCURRENT_BATCHES,
        "max_file_size_mb": settings.SCREENING_MAX_FILE_MB,
        "monthly_resume_limit": settings.SCREENING_MONTHLY_RESUME_LIMIT,
        "parser_version": settings.SCREENING_PARSER_VERSION,
        "scoring_version": settings.SCREENING_SCORING_VERSION,
    }


async def get_limits(provider: User, db: AsyncSession) -> ScreeningLimitsOut:
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used_q = await db.execute(
        select(func.coalesce(func.sum(ScreeningBatch.uploaded_count), 0)).where(
            ScreeningBatch.provider_id == provider.id,
            ScreeningBatch.created_at >= month_start,
            ScreeningBatch.status != "cancelled",
        )
    )
    used = int(used_q.scalar() or 0)
    return ScreeningLimitsOut(
        max_resumes_per_batch=settings.SCREENING_MAX_RESUMES_PER_BATCH,
        max_concurrent_batches=settings.SCREENING_MAX_CONCURRENT_BATCHES,
        max_file_size_mb=settings.SCREENING_MAX_FILE_MB,
        accepted_types=sorted(e.lstrip(".") for e in SCREENING_ALLOWED_EXT),
        monthly_resume_limit=settings.SCREENING_MONTHLY_RESUME_LIMIT,
        monthly_resumes_used=used,
    )


async def _assert_concurrent_ok(provider_id: str, db: AsyncSession) -> None:
    active = await db.execute(
        select(func.count()).select_from(ScreeningBatch).where(
            ScreeningBatch.provider_id == provider_id,
            ScreeningBatch.status.in_(["queued", "processing", "uploading"]),
        )
    )
    if int(active.scalar() or 0) >= settings.SCREENING_MAX_CONCURRENT_BATCHES:
        raise HTTPException(
            status_code=429,
            detail=f"Concurrent batch limit ({settings.SCREENING_MAX_CONCURRENT_BATCHES}) reached. Wait for active batches to finish.",
        )


async def get_owned_batch(batch_id: str, provider: User, db: AsyncSession, *, load: bool = False) -> ScreeningBatch:
    q = select(ScreeningBatch).where(
        ScreeningBatch.id == batch_id,
        ScreeningBatch.provider_id == provider.id,
    )
    if load:
        q = q.options(
            selectinload(ScreeningBatch.jds),
            selectinload(ScreeningBatch.resumes),
        )
    res = await db.execute(q)
    batch = res.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Screening batch not found")
    return batch


def _jd_out(jd: ScreeningJD) -> ScreeningJDOut:
    return ScreeningJDOut(
        id=str(jd.id),
        job_id=str(jd.job_id) if jd.job_id else None,
        is_manual=bool(jd.is_manual),
        title=jd.title,
        description=jd.description,
        location=jd.location,
        employment_type=jd.employment_type,
        required_skills=list(jd.required_skills or []),
        preferred_skills=list(jd.preferred_skills or []),
        min_experience_years=jd.min_experience_years,
        max_experience_years=jd.max_experience_years,
        education_requirements=jd.education_requirements,
    )


def _batch_summary(batch: ScreeningBatch, job_titles: Optional[List[str]] = None) -> ScreeningBatchSummary:
    titles = job_titles
    if titles is None and getattr(batch, "jds", None) is not None:
        titles = [j.title for j in batch.jds]
    return ScreeningBatchSummary(
        id=str(batch.id),
        name=batch.name,
        description=batch.description,
        status=batch.status,
        current_stage=batch.current_stage,
        total_files=batch.total_files or 0,
        uploaded_count=batch.uploaded_count or 0,
        parsed_count=batch.parsed_count or 0,
        matched_count=batch.matched_count or 0,
        failed_count=batch.failed_count or 0,
        skipped_count=batch.skipped_count or 0,
        pending_review_count=batch.pending_review_count or 0,
        progress_percent=float(batch.progress_percent or 0),
        job_titles=titles or [],
        created_at=batch.created_at,
        started_at=batch.started_at,
        completed_at=batch.completed_at,
        cancelled_at=batch.cancelled_at,
    )


async def create_batch(payload: ScreeningBatchCreate, provider: User, db: AsyncSession) -> ScreeningBatchDetail:
    if not payload.job_ids and not payload.manual_jds:
        raise HTTPException(status_code=400, detail="Select at least one job or add a manual job description.")

    await _assert_concurrent_ok(provider.id, db)

    jobs: List[JobPosting] = []
    if payload.job_ids:
        res = await db.execute(
            select(JobPosting).where(
                JobPosting.id.in_(payload.job_ids),
                JobPosting.provider_id == provider.id,
            )
        )
        jobs = list(res.scalars().all())
        found = {str(j.id) for j in jobs}
        missing = [jid for jid in payload.job_ids if jid not in found]
        if missing:
            raise HTTPException(status_code=403, detail="One or more jobs are not accessible for this provider.")

    batch = ScreeningBatch(
        provider_id=provider.id,
        created_by=provider.id,
        name=payload.name,
        description=payload.description,
        status="draft",
        current_stage="upload",
        limits_snapshot=_limits_snapshot(),
    )
    db.add(batch)
    await db.flush()

    for job in jobs:
        skills = list(job.required_skills or [])
        jd = ScreeningJD(
            batch_id=batch.id,
            job_id=job.id,
            is_manual=False,
            title=job.title,
            description=job.description,
            location=job.location,
            employment_type=job.employment_type,
            required_skills=skills,
            preferred_skills=[],
            min_experience_years=parse_experience_years(job.experience_required),
            education_requirements=None,
            normalized_required_skills=normalize_skills(skills),
            normalized_preferred_skills=[],
            jd_version="1",
            normalization_meta={"source": "job_posting"},
        )
        db.add(jd)

    for manual in payload.manual_jds:
        jd = ScreeningJD(
            batch_id=batch.id,
            job_id=None,
            is_manual=True,
            title=manual.title,
            description=manual.description,
            location=manual.location,
            employment_type=manual.employment_type,
            required_skills=list(manual.required_skills or []),
            preferred_skills=list(manual.preferred_skills or []),
            min_experience_years=manual.min_experience_years,
            max_experience_years=manual.max_experience_years,
            education_requirements=manual.education_requirements,
            normalized_required_skills=normalize_skills(manual.required_skills or []),
            normalized_preferred_skills=normalize_skills(manual.preferred_skills or []),
            jd_version="1",
            normalization_meta={"source": "manual"},
        )
        db.add(jd)

    db.add(ScreeningTaskEvent(
        batch_id=batch.id,
        event_type="batch_created",
        message="Screening batch created",
    ))
    await db.commit()
    return await get_batch_detail(str(batch.id), provider, db)


async def list_batches(
    provider: User,
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    has_pending_review: Optional[bool] = None,
    has_failed_files: Optional[bool] = None,
) -> ScreeningBatchListOut:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    filters = [ScreeningBatch.provider_id == provider.id]
    if status:
        filters.append(ScreeningBatch.status == status)
    if search:
        like = f"%{search.strip()}%"
        jd_match = (
            select(ScreeningJD.id)
            .where(
                ScreeningJD.batch_id == ScreeningBatch.id,
                ScreeningJD.title.ilike(like),
            )
            .exists()
        )
        filters.append(
            or_(
                ScreeningBatch.name.ilike(like),
                ScreeningBatch.description.ilike(like),
                jd_match,
            )
        )
    if has_pending_review:
        filters.append(ScreeningBatch.pending_review_count > 0)
    if has_failed_files:
        filters.append(ScreeningBatch.failed_count > 0)

    total_q = await db.execute(select(func.count()).select_from(ScreeningBatch).where(*filters))
    total = int(total_q.scalar() or 0)

    res = await db.execute(
        select(ScreeningBatch)
        .options(selectinload(ScreeningBatch.jds))
        .where(*filters)
        .order_by(ScreeningBatch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    batches = list(res.scalars().all())

    stats_q = await db.execute(
        select(
            func.count(ScreeningBatch.id),
            func.coalesce(func.sum(ScreeningBatch.parsed_count), 0),
            func.coalesce(func.sum(ScreeningBatch.pending_review_count), 0),
            func.coalesce(func.sum(ScreeningBatch.failed_count), 0),
        ).where(ScreeningBatch.provider_id == provider.id)
    )
    srow = stats_q.one()
    stats = ScreeningDashboardStats(
        total_batches=int(srow[0] or 0),
        resumes_processed=int(srow[1] or 0),
        awaiting_review=int(srow[2] or 0),
        failed_files=int(srow[3] or 0),
    )
    return ScreeningBatchListOut(
        items=[_batch_summary(b) for b in batches],
        total=total,
        page=page,
        page_size=page_size,
        stats=stats,
    )


async def get_batch_detail(batch_id: str, provider: User, db: AsyncSession) -> ScreeningBatchDetail:
    batch = await get_owned_batch(batch_id, provider, db, load=True)
    summary = _batch_summary(batch)
    failed_rows = (
        await db.execute(
            select(ScreeningBatchResume)
            .where(
                ScreeningBatchResume.batch_id == batch.id,
                ScreeningBatchResume.status == "failed",
            )
            .order_by(ScreeningBatchResume.original_filename.asc())
        )
    ).scalars().all()
    return ScreeningBatchDetail(
        **summary.model_dump(),
        jds=[_jd_out(j) for j in batch.jds],
        error_summary=batch.error_summary,
        limits_snapshot=batch.limits_snapshot,
        failed_files=[
            ScreeningFailedFileOut(
                id=str(r.id),
                original_filename=r.original_filename or "resume",
                error_code=r.error_code,
                error_message=r.error_message,
            )
            for r in failed_rows
        ],
    )


async def upload_resumes(
    batch_id: str,
    files: Sequence[UploadFile],
    provider: User,
    db: AsyncSession,
) -> ScreeningUploadResponse:
    batch = await get_owned_batch(batch_id, provider, db, load=True)
    if batch.status in ("processing", "queued", "completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot upload while batch is {batch.status}.")

    if batch.status == "draft":
        batch.status = "uploading"

    limits = await get_limits(provider, db)
    remaining_monthly = max(0, (limits.monthly_resume_limit or 0) - limits.monthly_resumes_used)
    capacity = settings.SCREENING_MAX_RESUMES_PER_BATCH - (batch.total_files or 0)

    uploaded: List[ScreeningUploadResult] = []
    rejected: List[dict] = []

    for f in files:
        if capacity <= 0:
            rejected.append({"filename": f.filename, "error": "Batch resume limit reached."})
            continue
        if remaining_monthly <= 0:
            rejected.append({"filename": f.filename, "error": "Monthly screening resume limit reached."})
            continue
        try:
            storage_key, original, size, digest, ftype = await save_screening_upload(
                f, str(provider.id), str(batch.id)
            )
        except HTTPException as he:
            rejected.append({"filename": getattr(f, "filename", None), "error": he.detail})
            continue
        except Exception:
            rejected.append({"filename": getattr(f, "filename", None), "error": "Upload failed."})
            continue

        # Duplicate content in this batch
        existing = await db.execute(
            select(ScreeningBatchResume).where(
                ScreeningBatchResume.batch_id == batch.id,
                ScreeningBatchResume.content_checksum == digest,
            )
        )
        if existing.scalar_one_or_none():
            delete_storage_key(storage_key)
            batch.skipped_count = (batch.skipped_count or 0) + 1
            uploaded.append(ScreeningUploadResult(
                id="",
                original_filename=original,
                file_size=size,
                status="skipped",
                detected_file_type=ftype,
                duplicate=True,
                error_message="Duplicate file content in this batch.",
            ))
            continue

        row = ScreeningBatchResume(
            batch_id=batch.id,
            storage_key=storage_key,
            original_filename=original,
            file_size=size,
            detected_file_type=ftype,
            content_checksum=digest,
            status="uploaded",
            extraction_status="pending",
        )
        db.add(row)
        await db.flush()
        batch.total_files = (batch.total_files or 0) + 1
        batch.uploaded_count = (batch.uploaded_count or 0) + 1
        capacity -= 1
        remaining_monthly -= 1
        uploaded.append(ScreeningUploadResult(
            id=str(row.id),
            original_filename=original,
            file_size=size,
            status="uploaded",
            detected_file_type=ftype,
            duplicate=False,
        ))

    await db.commit()
    detail = await get_batch_detail(batch_id, provider, db)
    return ScreeningUploadResponse(uploaded=uploaded, rejected=rejected, batch=detail)


async def remove_resume(batch_id: str, resume_id: str, provider: User, db: AsyncSession) -> ScreeningBatchDetail:
    batch = await get_owned_batch(batch_id, provider, db)
    if batch.status not in ("draft", "uploading", "failed", "partial"):
        raise HTTPException(status_code=400, detail="Cannot remove files after processing has started.")
    res = await db.execute(
        select(ScreeningBatchResume).where(
            ScreeningBatchResume.id == resume_id,
            ScreeningBatchResume.batch_id == batch.id,
        )
    )
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found in batch")
    delete_storage_key(row.storage_key)
    await db.delete(row)
    batch.total_files = max(0, (batch.total_files or 0) - 1)
    batch.uploaded_count = max(0, (batch.uploaded_count or 0) - 1)
    await db.commit()
    return await get_batch_detail(batch_id, provider, db)


async def start_processing(batch_id: str, provider: User, db: AsyncSession) -> ScreeningProgressOut:
    batch = await get_owned_batch(batch_id, provider, db, load=True)
    if not batch.jds:
        raise HTTPException(status_code=400, detail="Add at least one job description before starting.")
    if (batch.total_files or 0) < 1:
        raise HTTPException(status_code=400, detail="Upload at least one resume before starting.")
    if batch.status in ("processing", "queued"):
        return await get_progress(batch_id, provider, db)
    if batch.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cancelled batches cannot be started.")

    await _assert_concurrent_ok(provider.id, db)

    batch.status = "queued"
    batch.current_stage = "parse"
    batch.started_at = datetime.utcnow()
    batch.progress_percent = 1.0
    db.add(ScreeningTaskEvent(batch_id=batch.id, event_type="processing_started", message="Batch queued"))
    await db.commit()

    try:
        from app.modules.jobs_portal.services.screening_realtime import (
            progress_payload_from_batch,
            publish_screening_progress,
        )
        await publish_screening_progress(str(batch.id), progress_payload_from_batch(batch))
    except Exception:
        pass

    try:
        from app.shared.services.celery_tasks import process_screening_batch_task
        process_screening_batch_task.delay(str(batch.id))
    except Exception as exc:
        logger.warning("Failed to enqueue screening batch %s: %s", batch.id, exc)
        # Sync fallback for local/dev without workers
        try:
            from app.modules.jobs_portal.services.screening_pipeline import process_batch
            await process_batch(str(batch.id))
        except Exception as inner:
            batch = await get_owned_batch(batch_id, provider, db)
            batch.status = "failed"
            batch.error_summary = "Failed to start processing."
            await db.commit()
            raise HTTPException(status_code=500, detail="Failed to start screening processing.") from inner

    return await get_progress(batch_id, provider, db)


async def get_progress(batch_id: str, provider: User, db: AsyncSession) -> ScreeningProgressOut:
    batch = await get_owned_batch(batch_id, provider, db)
    pending = max(
        0,
        (batch.total_files or 0)
        - (batch.matched_count or 0)
        - (batch.failed_count or 0)
        - (batch.skipped_count or 0),
    )
    return ScreeningProgressOut(
        batch_id=str(batch.id),
        status=batch.status,
        current_stage=batch.current_stage,
        progress_percent=float(batch.progress_percent or 0),
        total_files=batch.total_files or 0,
        uploaded_count=batch.uploaded_count or 0,
        parsed_count=batch.parsed_count or 0,
        matched_count=batch.matched_count or 0,
        failed_count=batch.failed_count or 0,
        skipped_count=batch.skipped_count or 0,
        pending_count=pending,
        error_summary=batch.error_summary,
    )


async def cancel_batch(batch_id: str, provider: User, db: AsyncSession) -> ScreeningProgressOut:
    batch = await get_owned_batch(batch_id, provider, db)
    if batch.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a {batch.status} batch.")
    batch.status = "cancelled"
    batch.cancelled_at = datetime.utcnow()
    batch.current_stage = "done"
    db.add(ScreeningTaskEvent(batch_id=batch.id, event_type="batch_cancelled", message="Cancelled by provider"))
    await db.commit()
    return await get_progress(batch_id, provider, db)


async def retry_failed(batch_id: str, provider: User, db: AsyncSession) -> ScreeningProgressOut:
    batch = await get_owned_batch(batch_id, provider, db)
    res = await db.execute(
        select(ScreeningBatchResume).where(
            ScreeningBatchResume.batch_id == batch.id,
            ScreeningBatchResume.status == "failed",
        )
    )
    failed = list(res.scalars().all())
    if not failed:
        raise HTTPException(status_code=400, detail="No failed files to retry.")
    for row in failed:
        row.status = "uploaded"
        row.extraction_status = "pending"
        row.error_code = None
        row.error_message = None
        row.retry_count = (row.retry_count or 0) + 1
    batch.status = "queued"
    batch.current_stage = "parse"
    batch.failed_count = 0
    batch.error_summary = None
    db.add(ScreeningTaskEvent(batch_id=batch.id, event_type="retry_failed", message=f"Retrying {len(failed)} files"))
    await db.commit()
    try:
        from app.shared.services.celery_tasks import process_screening_batch_task
        process_screening_batch_task.delay(str(batch.id))
    except Exception:
        from app.modules.jobs_portal.services.screening_pipeline import process_batch
        await process_batch(str(batch.id))
    return await get_progress(batch_id, provider, db)


def _match_out(match: ScreeningCandidateMatch, profile: Optional[ScreeningResumeProfile], resume: ScreeningBatchResume) -> MatchResultOut:
    skills = []
    if profile and profile.skills:
        skills = profile.skills
    return MatchResultOut(
        match_id=str(match.id),
        batch_resume_id=str(match.batch_resume_id),
        screening_jd_id=str(match.screening_jd_id),
        candidate_name=profile.candidate_name if profile else None,
        candidate_email=profile.candidate_email if profile else None,
        candidate_location=profile.candidate_location if profile else None,
        experience_years=profile.experience_years if profile else None,
        skills=skills or [],
        overall_score=float(match.overall_score or 0),
        score_breakdown=match.score_breakdown,
        matched_requirements=list(match.matched_requirements or []),
        partially_matched_requirements=list(match.partially_matched_requirements or []),
        missing_requirements=list(match.missing_requirements or []),
        match_confidence=match.match_confidence,
        data_quality=match.data_quality,
        matching_status=match.matching_status,
        recruiter_decision=match.recruiter_decision or "none",
        fit_reason=match.fit_reason,
        original_filename=resume.original_filename,
        quality_status=profile.quality_status if profile else None,
    )


async def delete_batch(batch_id: str, provider: User, db: AsyncSession) -> dict:
    """Hard-delete a provider-owned screening batch (files + DB)."""
    batch = await get_owned_batch(batch_id, provider, db)
    # Soft-stop active runs so workers stop writing after delete.
    if batch.status in ("queued", "processing", "uploading", "parsing", "matching"):
        batch.status = "cancelled"
        batch.cancelled_at = datetime.utcnow()
        await db.flush()
    await hard_delete_screening_batch(db, batch)
    await db.commit()
    return {"ok": True, "deleted_id": batch_id}


async def list_results(
    batch_id: str,
    provider: User,
    db: AsyncSession,
    *,
    jd_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    search: Optional[str] = None,
    min_score: Optional[float] = None,
    decision: Optional[str] = None,
    quality_status: Optional[str] = None,
    sort: str = "score_desc",
) -> MatchResultsPage:
    batch = await get_owned_batch(batch_id, provider, db, load=True)
    jd: Optional[ScreeningJD] = None
    if jd_id:
        jd = next((j for j in batch.jds if str(j.id) == jd_id), None)
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found in batch")
    elif batch.jds:
        jd = batch.jds[0]
        jd_id = str(jd.id)

    page = max(1, page)
    page_size = min(100, max(1, page_size))

    q = (
        select(ScreeningCandidateMatch, ScreeningResumeProfile, ScreeningBatchResume)
        .join(ScreeningBatchResume, ScreeningBatchResume.id == ScreeningCandidateMatch.batch_resume_id)
        .outerjoin(ScreeningResumeProfile, ScreeningResumeProfile.batch_resume_id == ScreeningBatchResume.id)
        .where(ScreeningBatchResume.batch_id == batch.id)
    )
    if jd_id:
        q = q.where(ScreeningCandidateMatch.screening_jd_id == jd_id)
    if search:
        like = f"%{search.strip()}%"
        q = q.where(or_(
            ScreeningResumeProfile.candidate_name.ilike(like),
            ScreeningResumeProfile.candidate_email.ilike(like),
            ScreeningResumeProfile.candidate_location.ilike(like),
            ScreeningBatchResume.original_filename.ilike(like),
            cast(ScreeningResumeProfile.skills, String).ilike(like),
        ))
    if min_score is not None:
        q = q.where(ScreeningCandidateMatch.overall_score >= float(min_score))
    if decision:
        q = q.where(ScreeningCandidateMatch.recruiter_decision == decision)
    if quality_status:
        # Extraction issues: failed / poor / partial that require review
        if quality_status == "issues":
            q = q.where(or_(
                ScreeningResumeProfile.quality_status.in_(["failed", "poor"]),
                ScreeningResumeProfile.requires_review == True,  # noqa: E712
                ScreeningBatchResume.status == "failed",
            ))
        else:
            q = q.where(ScreeningResumeProfile.quality_status == quality_status)

    count_q = await db.execute(select(func.count()).select_from(q.subquery()))
    total = int(count_q.scalar() or 0)

    # Accept UI aliases (exp_desc) and full sort keys from column headers.
    if sort in ("score_asc",):
        q = q.order_by(ScreeningCandidateMatch.overall_score.asc(), ScreeningCandidateMatch.id.asc())
    elif sort in ("experience_desc", "exp_desc"):
        q = q.order_by(
            ScreeningResumeProfile.experience_years.desc().nullslast(),
            ScreeningCandidateMatch.overall_score.desc(),
        )
    elif sort in ("experience_asc", "exp_asc"):
        q = q.order_by(
            ScreeningResumeProfile.experience_years.asc().nullslast(),
            ScreeningCandidateMatch.overall_score.desc(),
        )
    elif sort in ("name_asc",):
        q = q.order_by(
            ScreeningResumeProfile.candidate_name.asc().nullslast(),
            ScreeningCandidateMatch.overall_score.desc(),
        )
    elif sort in ("name_desc",):
        q = q.order_by(
            ScreeningResumeProfile.candidate_name.desc().nullslast(),
            ScreeningCandidateMatch.overall_score.desc(),
        )
    elif sort in ("decision_asc",):
        q = q.order_by(
            ScreeningCandidateMatch.recruiter_decision.asc(),
            ScreeningCandidateMatch.overall_score.desc(),
        )
    elif sort in ("decision_desc",):
        q = q.order_by(
            ScreeningCandidateMatch.recruiter_decision.desc(),
            ScreeningCandidateMatch.overall_score.desc(),
        )
    else:
        # score_desc (default)
        q = q.order_by(ScreeningCandidateMatch.overall_score.desc(), ScreeningCandidateMatch.id.asc())

    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).all()
    items = [_match_out(m, p, r) for m, p, r in rows]
    return MatchResultsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        jd=_jd_out(jd) if jd else None,
    )


async def get_candidate_detail(
    batch_id: str,
    match_id: str,
    provider: User,
    db: AsyncSession,
) -> dict:
    batch = await get_owned_batch(batch_id, provider, db)
    res = await db.execute(
        select(ScreeningCandidateMatch, ScreeningResumeProfile, ScreeningBatchResume)
        .join(ScreeningBatchResume, ScreeningBatchResume.id == ScreeningCandidateMatch.batch_resume_id)
        .outerjoin(ScreeningResumeProfile, ScreeningResumeProfile.batch_resume_id == ScreeningBatchResume.id)
        .where(
            ScreeningCandidateMatch.id == match_id,
            ScreeningBatchResume.batch_id == batch.id,
        )
    )
    row = res.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate match not found")
    match, profile, resume = row
    return {
        "match": _match_out(match, profile, resume),
        "profile": profile.profile_json if profile else None,
        "evidence": {
            "matched": match.matched_requirements,
            "partial": match.partially_matched_requirements,
            "missing": match.missing_requirements,
            "relevant": match.relevant_evidence,
            "score_breakdown": match.score_breakdown,
        },
        "recruiter_notes": match.recruiter_notes,
        "resume_download_available": True,
        "extraction": {
            "method": profile.extraction_method if profile else None,
            "quality_status": profile.quality_status if profile else None,
            "requires_review": profile.requires_review if profile else True,
            "parser_version": profile.parser_version if profile else None,
        },
        "batch_resume_id": str(resume.id),
    }


async def update_decision(
    batch_id: str,
    match_id: str,
    payload: RecruiterDecisionIn,
    provider: User,
    db: AsyncSession,
) -> MatchResultOut:
    batch = await get_owned_batch(batch_id, provider, db)
    res = await db.execute(
        select(ScreeningCandidateMatch, ScreeningResumeProfile, ScreeningBatchResume)
        .join(ScreeningBatchResume, ScreeningBatchResume.id == ScreeningCandidateMatch.batch_resume_id)
        .outerjoin(ScreeningResumeProfile, ScreeningResumeProfile.batch_resume_id == ScreeningBatchResume.id)
        .where(
            ScreeningCandidateMatch.id == match_id,
            ScreeningBatchResume.batch_id == batch.id,
        )
    )
    row = res.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate match not found")
    match, profile, resume = row
    prev = match.recruiter_decision
    match.recruiter_decision = payload.decision
    if payload.notes is not None:
        match.recruiter_notes = payload.notes
    match.decision_by = provider.id
    match.decision_at = datetime.utcnow()
    if prev != "review" and payload.decision == "review":
        batch.pending_review_count = (batch.pending_review_count or 0) + 1
    elif prev == "review" and payload.decision != "review":
        batch.pending_review_count = max(0, (batch.pending_review_count or 0) - 1)
    db.add(ScreeningTaskEvent(
        batch_id=batch.id,
        batch_resume_id=resume.id,
        event_type="recruiter_decision",
        message=f"Decision set to {payload.decision}",
        meta={"match_id": str(match.id)},
    ))
    await db.commit()
    return _match_out(match, profile, resume)


async def bulk_decision(batch_id: str, payload: BulkDecisionIn, provider: User, db: AsyncSession) -> dict:
    updated = 0
    for mid in payload.match_ids:
        try:
            await update_decision(
                batch_id,
                mid,
                RecruiterDecisionIn(decision=payload.decision, notes=payload.notes),
                provider,
                db,
            )
            updated += 1
        except HTTPException:
            continue
    return {"updated": updated}


async def create_report(batch_id: str, payload: ReportCreateIn, provider: User, db: AsyncSession) -> ReportOut:
    batch = await get_owned_batch(batch_id, provider, db)
    if batch.status not in ("completed", "partial", "failed", "processing"):
        raise HTTPException(status_code=400, detail="Reports are available after processing has produced results.")
    report = ScreeningReport(
        batch_id=batch.id,
        report_type=payload.report_type,
        status="queued",
        created_by=provider.id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    try:
        from app.shared.services.celery_tasks import generate_screening_report_task
        generate_screening_report_task.delay(str(report.id))
    except Exception:
        from app.modules.jobs_portal.services.screening_report_service import generate_report
        await generate_report(str(report.id))
        await db.refresh(report)
    return ReportOut(
        id=str(report.id),
        batch_id=str(report.batch_id),
        report_type=report.report_type,
        status=report.status,
        file_size=report.file_size,
        error_message=report.error_message,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )


async def list_reports(batch_id: str, provider: User, db: AsyncSession) -> List[ReportOut]:
    batch = await get_owned_batch(batch_id, provider, db)
    res = await db.execute(
        select(ScreeningReport)
        .where(ScreeningReport.batch_id == batch.id)
        .order_by(ScreeningReport.created_at.desc())
    )
    return [
        ReportOut(
            id=str(r.id),
            batch_id=str(r.batch_id),
            report_type=r.report_type,
            status=r.status,
            file_size=r.file_size,
            error_message=r.error_message,
            created_at=r.created_at,
            completed_at=r.completed_at,
        )
        for r in res.scalars().all()
    ]


async def get_report_file(batch_id: str, report_id: str, provider: User, db: AsyncSession) -> Tuple[str, str, str]:
    """Returns (absolute_path, media_type, download_name)."""
    batch = await get_owned_batch(batch_id, provider, db)
    res = await db.execute(
        select(ScreeningReport).where(
            ScreeningReport.id == report_id,
            ScreeningReport.batch_id == batch.id,
        )
    )
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "ready" or not report.storage_key:
        raise HTTPException(status_code=409, detail="Report is not ready for download")
    path = resolve_storage_path(report.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report file missing")
    media = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    }.get(report.report_type, "application/octet-stream")
    name = f"screening-{batch_id}-{report.report_type}.{report.report_type}"
    return str(path), media, name


async def get_resume_file(batch_id: str, resume_id: str, provider: User, db: AsyncSession) -> Tuple[str, str]:
    batch = await get_owned_batch(batch_id, provider, db)
    res = await db.execute(
        select(ScreeningBatchResume).where(
            ScreeningBatchResume.id == resume_id,
            ScreeningBatchResume.batch_id == batch.id,
        )
    )
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")
    path = resolve_storage_path(row.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Resume file missing")
    return str(path), row.original_filename


# Terminal / abandoned statuses eligible for retention hard-delete.
# Active pipeline states (queued, processing, uploading) are never purged mid-run.
_RETENTION_PURGE_STATUSES = frozenset({
    "draft",
    "completed",
    "failed",
    "cancelled",
    "partial",
})


def batch_retention_anchor(batch: ScreeningBatch) -> datetime:
    """Reference timestamp for retention: completed → cancelled → created."""
    return batch.completed_at or batch.cancelled_at or batch.created_at


def is_eligible_for_retention_purge(batch: ScreeningBatch, cutoff: datetime) -> bool:
    if batch.status not in _RETENTION_PURGE_STATUSES:
        return False
    return batch_retention_anchor(batch) < cutoff


async def hard_delete_screening_batch(db: AsyncSession, batch: ScreeningBatch) -> None:
    """
    Hard-delete one provider-owned screening batch:
    remove private files, then DB row (cascades children).
    """
    provider_id = str(batch.provider_id)
    batch_id = str(batch.id)

    resumes = (
        await db.execute(
            select(ScreeningBatchResume).where(ScreeningBatchResume.batch_id == batch.id)
        )
    ).scalars().all()
    reports = (
        await db.execute(
            select(ScreeningReport).where(ScreeningReport.batch_id == batch.id)
        )
    ).scalars().all()

    for row in resumes:
        if row.storage_key:
            delete_storage_key(row.storage_key)
    for report in reports:
        if report.storage_key:
            delete_storage_key(report.storage_key)

    delete_provider_batch_dir(provider_id, batch_id)
    await db.delete(batch)


async def purge_expired_screening_batches(
    db: AsyncSession,
    *,
    retention_days: Optional[int] = None,
    limit: int = 200,
) -> dict:
    """
    Hard-delete provider screening batches past SCREENING_RETENTION_DAYS.
    Only provider-owned batches (all screening batches are); never touches
    other upload trees. Safe to run from Celery beat.
    """
    days = retention_days if retention_days is not None else settings.SCREENING_RETENTION_DAYS
    days = max(1, int(days))
    cutoff = datetime.utcnow() - timedelta(days=days)
    # completed_at → cancelled_at → created_at (matches batch_retention_anchor)
    retention_anchor = func.coalesce(
        ScreeningBatch.completed_at,
        ScreeningBatch.cancelled_at,
        ScreeningBatch.created_at,
    )

    res = await db.execute(
        select(ScreeningBatch)
        .where(
            ScreeningBatch.status.in_(list(_RETENTION_PURGE_STATUSES)),
            retention_anchor < cutoff,
        )
        .order_by(retention_anchor.asc())
        .limit(max(1, int(limit)))
    )
    candidates = list(res.scalars().all())
    purged = 0
    errors = 0
    for batch in candidates:
        # Defense in depth — never purge active pipeline batches
        if not is_eligible_for_retention_purge(batch, cutoff):
            continue
        try:
            await hard_delete_screening_batch(db, batch)
            await db.flush()
            purged += 1
        except Exception:
            errors += 1
            logger.exception(
                "Failed retention purge for screening batch %s (provider %s)",
                batch.id,
                batch.provider_id,
            )

    await db.commit()
    return {
        "ok": True,
        "retention_days": days,
        "cutoff": cutoff.isoformat() + "Z",
        "purged": purged,
        "errors": errors,
    }
