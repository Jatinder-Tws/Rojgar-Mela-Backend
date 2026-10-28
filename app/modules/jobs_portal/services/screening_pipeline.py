"""Background processing pipeline: parse once → match all JDs → update progress."""

from __future__ import annotations

import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.modules.jobs_portal.models.screening import (
    ScreeningBatch,
    ScreeningBatchResume,
    ScreeningCandidateMatch,
    ScreeningResumeProfile,
    ScreeningTaskEvent,
)
from app.modules.jobs_portal.services.screening_extraction import extract_screening_profile
from app.modules.jobs_portal.services.screening_matching import (
    ai_audit_match,
    score_candidate_against_jd,
)
from app.modules.jobs_portal.services.screening_realtime import (
    progress_payload_from_batch,
    publish_screening_progress,
)
from app.modules.jobs_portal.services.screening_storage import resolve_storage_path

logger = logging.getLogger(__name__)


async def _refresh_counts(db, batch: ScreeningBatch) -> None:
    resumes = (
        await db.execute(select(ScreeningBatchResume).where(ScreeningBatchResume.batch_id == batch.id))
    ).scalars().all()
    parsed = sum(1 for r in resumes if r.status in ("extracted", "matched", "matching"))
    matched = sum(1 for r in resumes if r.status == "matched")
    failed = sum(1 for r in resumes if r.status == "failed")
    skipped = sum(1 for r in resumes if r.status == "skipped")
    total = len(resumes) or 1
    batch.parsed_count = parsed
    batch.matched_count = matched
    batch.failed_count = failed
    batch.skipped_count = skipped
    # progress: parse 50% + match 50%
    batch.progress_percent = round(min(99.0, (parsed / total) * 50 + (matched / total) * 50), 2)


async def process_single_resume(db, batch: ScreeningBatch, resume: ScreeningBatchResume) -> None:
    if batch.status == "cancelled":
        resume.status = "cancelled"
        return

    resume.status = "parsing"
    resume.extraction_status = "parsing"
    await db.flush()

    try:
        path = resolve_storage_path(resume.storage_key)
    except Exception:
        resume.status = "failed"
        resume.error_code = "storage_error"
        resume.error_message = "Could not locate uploaded file."
        return

    if not path.is_file():
        resume.status = "failed"
        resume.error_code = "file_missing"
        resume.error_message = "Uploaded file is missing."
        return

    profile_data = extract_screening_profile(str(path), resume.original_filename)
    extraction = profile_data.get("extraction") or {}
    if extraction.get("quality_status") == "failed":
        resume.status = "failed"
        resume.extraction_status = "failed"
        resume.error_code = extraction.get("error") or "extraction_failed"
        resume.error_message = (
            extraction.get("error_message")
            or "Could not extract usable text from this resume. "
            "It may be a scanned/image PDF, password-protected, or corrupt."
        )
        db.add(ScreeningTaskEvent(
            batch_id=batch.id,
            batch_resume_id=resume.id,
            event_type="extract_failed",
            error_class=resume.error_code or "extraction_failed",
            message=resume.error_message,
        ))
        return

    full_text = profile_data.pop("_full_text", "") or ""
    cand = profile_data.get("candidate") or {}

    existing = (
        await db.execute(
            select(ScreeningResumeProfile).where(ScreeningResumeProfile.batch_resume_id == resume.id)
        )
    ).scalar_one_or_none()

    profile_row = existing or ScreeningResumeProfile(batch_resume_id=resume.id)
    profile_row.schema_version = profile_data.get("schema_version") or "1.0"
    profile_row.extraction_method = extraction.get("method")
    profile_row.quality_status = extraction.get("quality_status")
    profile_row.requires_review = bool(extraction.get("requires_review"))
    profile_row.parser_version = extraction.get("parser_version") or settings.SCREENING_PARSER_VERSION
    profile_row.candidate_name = cand.get("name")
    profile_row.candidate_email = cand.get("email")
    profile_row.candidate_phone = cand.get("phone")
    profile_row.candidate_location = cand.get("location")
    profile_row.experience_years = profile_data.get("experience_years")
    profile_row.skills = profile_data.get("skills")
    profile_row.experience = profile_data.get("experience")
    profile_row.education = profile_data.get("education")
    profile_row.projects = profile_data.get("projects")
    profile_row.certifications = profile_data.get("certifications")
    profile_row.profile_json = {
        k: v for k, v in profile_data.items() if k != "_full_text"
    }
    profile_row.raw_text_excerpt = profile_data.get("raw_text_excerpt")
    profile_row.evidence = profile_data.get("evidence")
    if not existing:
        db.add(profile_row)

    resume.status = "extracted"
    resume.extraction_status = "extracted"
    resume.extraction_version = settings.SCREENING_PARSER_VERSION
    resume.parsed_at = datetime.utcnow()
    await db.flush()

    # Match once-extracted profile against every JD
    resume.status = "matching"
    jds = batch.jds or []
    for jd in jds:
        if batch.status == "cancelled":
            break
        existing_match = (
            await db.execute(
                select(ScreeningCandidateMatch).where(
                    ScreeningCandidateMatch.batch_resume_id == resume.id,
                    ScreeningCandidateMatch.screening_jd_id == jd.id,
                )
            )
        ).scalar_one_or_none()

        profile_payload = {
            "skills": profile_row.skills,
            "experience_years": profile_row.experience_years,
            "education": profile_row.education,
            "experience": profile_row.experience,
            "raw_text_excerpt": profile_row.raw_text_excerpt,
            "extraction": {"quality_status": profile_row.quality_status},
            "quality_status": profile_row.quality_status,
        }
        jd_payload = {
            "title": jd.title,
            "required_skills": jd.required_skills,
            "preferred_skills": jd.preferred_skills,
            "normalized_required_skills": jd.normalized_required_skills,
            "normalized_preferred_skills": jd.normalized_preferred_skills,
            "min_experience_years": jd.min_experience_years,
            "max_experience_years": jd.max_experience_years,
            "education_requirements": jd.education_requirements,
            "description": jd.description,
        }
        score = score_candidate_against_jd(
            profile_payload,
            jd_payload,
            evidence_text=full_text or (profile_row.raw_text_excerpt or ""),
        )
        if score.get("needs_ai_audit"):
            score = await ai_audit_match(profile_payload, jd_payload, score)

        match = existing_match or ScreeningCandidateMatch(
            batch_resume_id=resume.id,
            screening_jd_id=jd.id,
        )
        match.overall_score = score["overall_score"]
        match.score_breakdown = score["score_breakdown"]
        match.matched_requirements = score["matched_requirements"]
        match.partially_matched_requirements = score["partially_matched_requirements"]
        match.missing_requirements = score["missing_requirements"]
        match.relevant_evidence = score["relevant_evidence"]
        match.match_confidence = score["match_confidence"]
        match.data_quality = score["data_quality"]
        match.scoring_version = score["scoring_version"]
        match.matching_status = "matched"
        match.fit_reason = score["fit_reason"]
        if not existing_match:
            db.add(match)

    resume.status = "matched"
    resume.matched_at = datetime.utcnow()
    db.add(ScreeningTaskEvent(
        batch_id=batch.id,
        batch_resume_id=resume.id,
        event_type="resume_matched",
        message="Resume extracted and matched",
    ))


async def process_batch(batch_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(ScreeningBatch)
            .options(
                selectinload(ScreeningBatch.jds),
                selectinload(ScreeningBatch.resumes),
            )
            .where(ScreeningBatch.id == batch_id)
        )
        batch = res.scalar_one_or_none()
        if not batch:
            return {"ok": False, "error": "not_found"}
        if batch.status == "cancelled":
            return {"ok": False, "error": "cancelled"}

        batch.status = "processing"
        batch.current_stage = "parse"
        await db.commit()
        try:
            await publish_screening_progress(str(batch.id), progress_payload_from_batch(batch))
        except Exception:
            pass

        # Reload after commit
        res = await db.execute(
            select(ScreeningBatch)
            .options(
                selectinload(ScreeningBatch.jds),
                selectinload(ScreeningBatch.resumes),
            )
            .where(ScreeningBatch.id == batch_id)
        )
        batch = res.scalar_one()

        chunk = max(1, settings.SCREENING_CHUNK_SIZE)
        pending = [
            r for r in batch.resumes
            if r.status in ("uploaded", "parsing", "matching")
            or (r.status == "failed" and (r.extraction_status or "") == "pending")
        ]

        for i in range(0, len(pending), chunk):
            # re-check cancel
            await db.refresh(batch)
            if batch.status == "cancelled":
                await db.commit()
                return {"ok": False, "error": "cancelled"}

            for resume in pending[i : i + chunk]:
                await db.refresh(batch)
                if batch.status == "cancelled":
                    break
                try:
                    await process_single_resume(db, batch, resume)
                except Exception as exc:
                    logger.exception("screening resume %s failed", resume.id)
                    resume.status = "failed"
                    resume.error_code = "processing_error"
                    resume.error_message = "Processing failed for this file."
                    db.add(ScreeningTaskEvent(
                        batch_id=batch.id,
                        batch_resume_id=resume.id,
                        event_type="processing_error",
                        error_class=type(exc).__name__,
                        message="Processing failed",
                    ))
                await _refresh_counts(db, batch)
                await db.commit()
                try:
                    await publish_screening_progress(str(batch.id), progress_payload_from_batch(batch))
                except Exception:
                    pass

        await db.refresh(batch)
        if batch.status == "cancelled":
            try:
                await publish_screening_progress(str(batch.id), progress_payload_from_batch(batch))
            except Exception:
                pass
            return {"ok": False, "error": "cancelled"}

        await _refresh_counts(db, batch)
        if (batch.failed_count or 0) > 0 and (batch.matched_count or 0) > 0:
            batch.status = "partial"
        elif (batch.failed_count or 0) > 0 and (batch.matched_count or 0) == 0:
            batch.status = "failed"
            batch.error_summary = "All resumes failed processing."
        else:
            batch.status = "completed"
        batch.current_stage = "done"
        batch.progress_percent = 100.0
        batch.completed_at = datetime.utcnow()
        db.add(ScreeningTaskEvent(batch_id=batch.id, event_type="batch_completed", message=f"Status={batch.status}"))
        await db.commit()
        try:
            await publish_screening_progress(str(batch.id), progress_payload_from_batch(batch))
        except Exception:
            pass
        return {
            "ok": True,
            "status": batch.status,
            "matched": batch.matched_count,
            "failed": batch.failed_count,
        }
