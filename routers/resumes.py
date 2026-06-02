from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from schemas.resume import ResumeResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse
import os

from database import get_db
from models.resume import Resume
from models.user import User
from schemas.jobs import ResumeImproveRequest, ResumeOut
from services.auth_service import require_seeker
from services.file_service import save_upload
from services.resume_parser import parse_resume
from services.seeker_matching_service import embed_and_store_resume
from services.auth_service import require_provider
# from services.ai_improvement_suggestion_service import analyze_resume
from services.ai_improvement_suggestion_service import  analyze_resume_multi
router = APIRouter(prefix="/resumes", tags=["resumes"])


import logging
logger = logging.getLogger(__name__)


async def _process_resume(resume_id: str, file_path: str, filename: str) -> None:
    """Background task: invalidate old matches, re-embed the resume, and find matching jobs."""
    try:
        from database import AsyncSessionLocal
        from services.seeker_matching_service import embed_and_store_resume, proactive_match_resume_to_jobs
        from sqlalchemy import text as sa_text
        async with AsyncSessionLocal() as s:
            res = await s.get(Resume, resume_id)
            if not res:
                logger.error(f"[RESUME] ID {resume_id} not found in DB for embedding")
                return
            if not res.parsed_text:
                logger.warning(f"[RESUME] {resume_id} has no parsed_text - skipping embed")
                return
            
            # Step 0: Delete stale matches for this seeker
            await s.execute(
                sa_text("DELETE FROM matches WHERE seeker_id = :sid"),
                {"sid": res.user_id},
            )
            await s.commit()
            logger.info(f"[RESUME] Cleared old matches for seeker {res.user_id}")
            
            # Step 1: Generate and store embedding
            await embed_and_store_resume(res, s)
            logger.info(f"[RESUME] Embedding complete for {resume_id}")
            
            # Step 2: Find and store all matching jobs
            await proactive_match_resume_to_jobs(resume_id)
            logger.info(f"[RESUME] Proactive matching complete for {resume_id}")
            
    except Exception as e:
        logger.exception(f"[RESUME] Background processing failed for {resume_id}: {e}")


@router.post("/upload", response_model=ResumeOut, status_code=201)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    file_path, filename, size_bytes = await save_upload(file, str(user.id))

    # Parse resume text synchronously now (fast, no network calls)
    try:
        raw_text, parsed_json = parse_resume(file_path, filename)
    except Exception as e:
        logger.warning(f"[RESUME] Parse failed for {filename}: {e}")
        raw_text, parsed_json = "", {}

    # Upsert: update existing resume if user already has one
    existing_result = await db.execute(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).limit(1)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.filename = filename
        existing.file_path = file_path
        existing.file_size_bytes = size_bytes
        existing.parsed_text = raw_text
        existing.parsed_json = parsed_json
        existing.embedding = None  # clear stale embedding; bg task will re-embed
        await db.commit()
        await db.refresh(existing)
        resume = existing
    else:
        resume = Resume(
            user_id=user.id,
            filename=filename,
            file_path=file_path,
            file_size_bytes=size_bytes,
            parsed_text=raw_text,
            parsed_json=parsed_json,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

    # Embed in background (requires OpenAI call – async)
    background_tasks.add_task(_process_resume, resume.id, file_path, filename)

    return ResumeOut.model_validate(resume)



@router.get("/me", response_model=ResumeOut)
async def get_my_resume(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user.id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume uploaded yet")
    return ResumeOut.model_validate(resume)


@router.get("/me/download")
async def download_my_resume(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    """Download the actual resume file."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user.id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume = result.scalar_one_or_none()
    if not resume or not resume.file_path:
        raise HTTPException(status_code=404, detail="No resume uploaded yet")
    
    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file not found on server")
    
    media_type = "application/pdf" if resume.filename.lower().endswith(".pdf") else "application/octet-stream"
    return FileResponse(
        path=resume.file_path,
        filename=resume.filename,
        media_type=media_type
    )

@router.get("/{user_id}/download")
async def download_candidate_resume(
    user_id: str,
    provider: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    """Provider: Download a specific candidate's resume."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume = result.scalar_one_or_none()
    if not resume or not resume.file_path:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file not found on server")
    
    media_type = "application/pdf" if resume.filename.lower().endswith(".pdf") else "application/octet-stream"
    return FileResponse(
        path=resume.file_path,
        filename=resume.filename,
        media_type=media_type
    )

@router.get("/{user_id}/status")
async def check_candidate_resume_status(
    user_id: str,
    provider: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    """Provider: Check if a specific candidate has a resume available."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume = result.scalar_one_or_none()
    if not resume or not resume.file_path or not os.path.exists(resume.file_path):
        return {"has_resume": False, "filename": None}
    
    return {"has_resume": True, "filename": resume.filename}


@router.post("/resume/improve",response_model=ResumeResponse)
async def improve_resume(
    request:ResumeImproveRequest,
    db: AsyncSession = Depends(get_db),

):
    tech_list = [t.strip() for t in request.technologies.split(",")]

    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == request.user_id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume = result.scalars().first()


    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # ai_result = await analyze_resume(
    #     data={
    #         "job_title": job_title,
    #         "job_description": job_description,
    #         "technologies": tech_list
    #     },
    #     resume_text=resume.parsed_json  
    # )

    ai_result = await analyze_resume_multi(
        data={
            "job_title": request.job_title,
            "job_description": request.job_description,
            "technologies": tech_list
        },
        resume_text=resume.parsed_json  
    )
    print("AI RESULT:", ai_result)

    return ai_result