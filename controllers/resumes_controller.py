import os
import uuid
import re
import logging
from datetime import datetime
from pathlib import Path
from fastapi import BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portfolio import Portfolio
from models.resume import Resume
from models.user import User
from schemas.jobs import ResumeImproveRequest, ResumeOut, ResumeProcessingStatusOut
from schemas.resume import ResumeResponse
from services.file_service import save_upload
from services.resume_parser import parse_resume, extract_profile_fields_with_ai
from services.ai_improvement_suggestion_service import analyze_resume_multi

logger = logging.getLogger(__name__)


def _split_name(full_name: str | None) -> tuple[str | None, str | None]:
    if not full_name:
        return None, None
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _to_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


async def _get_or_create_portfolio(db: AsyncSession, user_id: str) -> Portfolio:
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
    portfolio = result.scalar_one_or_none()
    if portfolio:
        return portfolio
    portfolio = Portfolio(user_id=user_id)
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _set_portfolio_str(portfolio: Portfolio, field: str, value) -> None:
    if _is_empty(value) or not _is_empty(getattr(portfolio, field, None)):
        return
    setattr(portfolio, field, str(value).strip())


def _normalize_skills(skills, parsed_json: dict) -> list:
    normalized = []
    if isinstance(skills, list):
        for item in skills:
            if isinstance(item, dict) and item.get("name"):
                normalized.append({"name": str(item["name"]).strip(), "level": str(item.get("level") or "Intermediate").strip()})
            elif isinstance(item, str) and item.strip():
                normalized.append({"name": item.strip(), "level": "Intermediate"})
    if not normalized and parsed_json.get("skills"):
        normalized = [{"name": s, "level": "Intermediate"} for s in parsed_json["skills"]]
    return normalized


def _normalize_list_items(items: list, shape: dict) -> list:
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = {key: item.get(key) for key in shape}
        if any(not _is_empty(v) for v in row.values()):
            out.append(row)
    return out


def _map_resume_to_user(user: User, ai_data: dict, parsed_json: dict) -> None:
    first_name = ai_data.get("first_name")
    last_name = ai_data.get("last_name")
    if not first_name and ai_data.get("full_name"):
        split_first, split_last = _split_name(ai_data.get("full_name"))
        first_name = split_first
        last_name = last_name or split_last
    if not user.first_name and first_name:
        user.first_name = str(first_name).strip()
    if not user.last_name and last_name:
        user.last_name = str(last_name).strip()
    if not user.email and ai_data.get("email"):
        user.email = str(ai_data["email"]).strip().lower()
    if ai_data.get("phone") and (not user.phone or user.phone.strip() in ("", "0000000000")):
        phone = re.sub(r"\D", "", str(ai_data["phone"]))
        if len(phone) >= 10:
            user.phone = phone[-10:]
    if parsed_json.get("experience_years") is not None:
        user.experience = f"{parsed_json['experience_years']} years"
    if ai_data.get("highest_qualification"):
        user.highest_qualification = str(ai_data["highest_qualification"]).strip()
    if ai_data.get("stream_specialization"):
        user.stream_specialization = str(ai_data["stream_specialization"]).strip()
    if ai_data.get("college_institute_name"):
        user.college_institute_name = str(ai_data["college_institute_name"]).strip()
    if ai_data.get("preferred_job_sector"):
        user.preferred_job_sector = str(ai_data["preferred_job_sector"]).strip()
    if ai_data.get("job_role"):
        user.job_role = str(ai_data["job_role"]).strip()


def _map_resume_to_portfolio(portfolio: Portfolio, ai_data: dict, parsed_json: dict) -> None:
    for field in ("headline", "bio", "date_of_birth", "gender", "city", "state", "linkedin_url", "github_url", "website_url", "current_company", "current_role"):
        _set_portfolio_str(portfolio, field, ai_data.get(field))
    exp_years = _to_float(ai_data.get("total_experience_years"))
    if exp_years is None and parsed_json.get("experience_years") is not None:
        exp_years = _to_float(parsed_json.get("experience_years"))
    if exp_years is not None and portfolio.total_experience_years is None:
        portfolio.total_experience_years = exp_years
    if _is_empty(portfolio.skills):
        skills = _normalize_skills(ai_data.get("skills"), parsed_json)
        if skills:
            portfolio.skills = skills
    if _is_empty(portfolio.work_experiences):
        work = _normalize_list_items(ai_data.get("work_experiences") or [], {"company": None, "role": None, "start_date": None, "end_date": None, "description": None, "is_current": False})
        for row in work:
            row["is_current"] = bool(row.get("is_current"))
        if work:
            portfolio.work_experiences = work
    if _is_empty(portfolio.education):
        education = _normalize_list_items(ai_data.get("education") or [], {"institution": None, "degree": None, "field": None, "start_year": None, "end_year": None})
        if education:
            portfolio.education = education
    if _is_empty(portfolio.certifications):
        certs = _normalize_list_items(ai_data.get("certifications") or [], {"name": None, "issuer": None, "date": None, "url": None})
        if certs:
            portfolio.certifications = certs
    if _is_empty(portfolio.languages):
        langs = _normalize_list_items(ai_data.get("languages") or [], {"language": None, "proficiency": "Conversational"})
        if langs:
            portfolio.languages = langs
    if _is_empty(portfolio.projects):
        projects = []
        for item in ai_data.get("projects") or []:
            if not isinstance(item, dict) or not item.get("title"):
                continue
            tech = item.get("technologies")
            projects.append({"title": str(item.get("title")).strip(), "description": item.get("description"), "url": item.get("url"), "technologies": tech if isinstance(tech, list) else []})
        if projects:
            portfolio.projects = projects


def _get_processing_meta(parsed_json: dict | None) -> dict:
    if not isinstance(parsed_json, dict):
        return {}
    meta = parsed_json.get("_processing")
    return meta if isinstance(meta, dict) else {}


def _attach_processing_meta(parsed_json: dict | None, status: str, message: str, **extra) -> dict:
    base = dict(parsed_json or {})
    base["_processing"] = {"status": status, "message": message, "updated_at": datetime.utcnow().isoformat(), **extra}
    return base


async def _update_resume_processing(resume_id: str, status: str, message: str, **extra) -> None:
    from database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as s:
            res = await s.get(Resume, resume_id)
            if not res:
                return
            res.parsed_json = _attach_processing_meta(res.parsed_json if isinstance(res.parsed_json, dict) else {}, status, message, **extra)
            await s.commit()
    except Exception as e:
        logger.warning(f"[RESUME] Failed to update processing status for {resume_id}: {e}")


def _resume_status_out(resume: Resume | None) -> ResumeProcessingStatusOut:
    if not resume:
        return ResumeProcessingStatusOut(has_resume=False, processing_status="idle")
    meta = _get_processing_meta(resume.parsed_json if isinstance(resume.parsed_json, dict) else {})
    return ResumeProcessingStatusOut(
        has_resume=True,
        resume_id=str(resume.id),
        filename=resume.filename,
        processing_status=meta.get("status") or "completed",
        processing_message=meta.get("message"),
        ocr_used=bool(meta.get("ocr_used")),
        profile_mapped=bool(meta.get("profile_mapped")),
    )


async def _process_resume(resume_id: str, file_path: str, filename: str) -> None:
    try:
        from database import AsyncSessionLocal
        from services.seeker_matching_service import embed_and_store_resume, proactive_match_resume_to_jobs
        from sqlalchemy import text as sa_text

        await _update_resume_processing(resume_id, "embedding", "Generating AI embedding for job matching…")
        async with AsyncSessionLocal() as s:
            res = await s.get(Resume, resume_id)
            if not res:
                await _update_resume_processing(resume_id, "failed", "Resume record not found.")
                return
            if not res.parsed_text:
                ext = Path(filename).suffix.lower()
                msg = (
                    "Could not read this .doc file. Save it as .docx or PDF and upload again."
                    if ext == ".doc"
                    else "Could not extract text from resume. Try a clearer PDF or DOCX."
                )
                await _update_resume_processing(resume_id, "failed", msg)
                return
            from models.match import Match
            from sqlalchemy import delete
            await s.execute(delete(Match).where(Match.seeker_id == res.user_id))
            await s.commit()
            await embed_and_store_resume(res, s)

        await _update_resume_processing(resume_id, "matching", "Finding jobs that match your profile…")
        await proactive_match_resume_to_jobs(resume_id)
        await _update_resume_processing(resume_id, "completed", "Resume processed. Your profile and job matches are ready.")
    except Exception as e:
        logger.exception(f"[RESUME] Background processing failed for {resume_id}: {e}")
        await _update_resume_processing(resume_id, "failed", "Background job matching failed. Your profile was still saved.")


async def upload_resume(background_tasks: BackgroundTasks, file: UploadFile, user: User, db: AsyncSession) -> ResumeOut:
    file_path, filename, size_bytes = await save_upload(file, str(user.id))
    parse_error: str | None = None
    try:
        raw_text, parsed_json = parse_resume(file_path, filename)
    except Exception as e:
        logger.warning(f"[RESUME] Parse failed for {filename}: {e}")
        parse_error = str(e).strip()
        raw_text, parsed_json = "", {}

    if not (raw_text or "").strip():
        ext = Path(filename).suffix.lower()
        if not parse_error:
            if ext == ".doc":
                parse_error = (
                    "Could not read this .doc file. Save it as .docx or PDF in Word and upload again."
                )
            else:
                parse_error = "Could not extract text from resume. Try a clearer PDF or DOCX."
        raise HTTPException(status_code=400, detail=parse_error)
    ocr_used = bool(raw_text) and len(raw_text.strip()) < 300 and filename.lower().endswith(".pdf")

    ai_profile_data = {}
    try:
        ai_profile_data = await extract_profile_fields_with_ai(raw_text, parsed_json)
    except Exception as e:
        logger.warning(f"[RESUME] AI extraction failed for {filename}: {e}")

    profile_mapped = bool(ai_profile_data) or bool(parsed_json)
    final_parsed = {**(parsed_json or {}), "ai_profile_data": ai_profile_data}
    final_parsed = _attach_processing_meta(final_parsed, "queued", "Profile saved. Job matching is running in the background…", ocr_used=ocr_used, profile_mapped=profile_mapped)

    existing_result = await db.execute(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).limit(1))
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.filename = filename
        existing.file_path = file_path
        existing.file_size_bytes = size_bytes
        existing.parsed_text = raw_text
        existing.parsed_json = final_parsed
        existing.embedding = None
        portfolio = await _get_or_create_portfolio(db, str(user.id))
        _map_resume_to_user(user, ai_profile_data, parsed_json)
        _map_resume_to_portfolio(portfolio, ai_profile_data, parsed_json)
        await db.commit()
        await db.refresh(existing)
        resume = existing
    else:
        resume = Resume(user_id=user.id, filename=filename, file_path=file_path, file_size_bytes=size_bytes, parsed_text=raw_text, parsed_json=final_parsed)
        db.add(resume)
        portfolio = await _get_or_create_portfolio(db, str(user.id))
        _map_resume_to_user(user, ai_profile_data, parsed_json)
        _map_resume_to_portfolio(portfolio, ai_profile_data, parsed_json)
        await db.commit()
        await db.refresh(resume)

    background_tasks.add_task(_process_resume, resume.id, file_path, filename)
    return ResumeOut.model_validate(resume)


async def get_my_resume_processing_status(user: User, db: AsyncSession) -> ResumeProcessingStatusOut:
    result = await db.execute(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).limit(1))
    return _resume_status_out(result.scalar_one_or_none())


async def get_my_resume(user: User, db: AsyncSession) -> ResumeOut:
    result = await db.execute(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).limit(1))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume uploaded yet")
    return ResumeOut.model_validate(resume)


async def download_my_resume(user: User, db: AsyncSession) -> FileResponse:
    result = await db.execute(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).limit(1))
    resume = result.scalar_one_or_none()
    if not resume or not resume.file_path:
        raise HTTPException(status_code=404, detail="No resume uploaded yet")
    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file not found on server")
    media_type = "application/pdf" if resume.filename.lower().endswith(".pdf") else "application/octet-stream"
    return FileResponse(path=resume.file_path, filename=resume.filename, media_type=media_type)


async def download_candidate_resume(user_id: str, db: AsyncSession) -> FileResponse:
    result = await db.execute(select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc()).limit(1))
    resume = result.scalar_one_or_none()
    if not resume or not resume.file_path:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file not found on server")
    media_type = "application/pdf" if resume.filename.lower().endswith(".pdf") else "application/octet-stream"
    return FileResponse(path=resume.file_path, filename=resume.filename, media_type=media_type)


async def check_candidate_resume_status(user_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc()).limit(1))
    resume = result.scalar_one_or_none()
    if not resume or not resume.file_path or not os.path.exists(resume.file_path):
        return {"has_resume": False, "filename": None}
    return {"has_resume": True, "filename": resume.filename}


async def improve_resume(request: ResumeImproveRequest, db: AsyncSession) -> dict:
    result = await db.execute(select(Resume).where(Resume.user_id == request.user_id).order_by(Resume.created_at.desc()).limit(1))
    resume = result.scalars().first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    from services.celery_tasks import improve_resume_task
    task = improve_resume_task.delay(
        job_title=request.job_title,
        job_description=request.job_description,
        technologies=request.technologies,
        user_id=request.user_id
    )
    return {"task_id": task.id, "status": "PENDING"}

