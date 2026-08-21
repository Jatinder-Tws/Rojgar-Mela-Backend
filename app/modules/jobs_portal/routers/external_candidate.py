import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, File, UploadFile, Form, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.modules.jobs_portal.models.application import Application, ApplicationStatus
from app.modules.jobs_portal.models.external_candidate import ExternalCandidate
from app.modules.jobs_portal.models.external_candidate_match import ExternalCandidateMatch
from app.modules.jobs_portal.models.job import JobPosting
from app.shared.models.user import User, UserRole
from app.shared.models.imported_user_password import ImportedUserPassword
from app.modules.jobs_portal.schemas.external_candidate import ExternalCandidateCreate, ExternalCandidateOut, ExternalCandidateMatchOut
from app.core.dependencies import hash_password, generate_secure_password
from app.shared.services.email_service import send_job_fair_welcome_email, send_welcome_email
from app.modules.jobs_portal.services.public_jobs_service import (
    search_public_jobs,
    get_job_suggestions,
    get_job_browse_meta,
    serialize_public_job_detail,
    get_similar_jobs,
    get_job_filter_facets,
)
from app.core.config import settings
from typing import List

router = APIRouter(prefix="/external", tags=["External Candidates"])

@router.post("/apply", response_model=ExternalCandidateOut)
async def apply_for_job(
    background_tasks: BackgroundTasks,
    candidate_data: str = Form(...),
    resume: UploadFile = File(None),
    profile_picture: UploadFile = File(None),
    salary_slip: UploadFile = File(None),
    experience_letter: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Publicly accessible endpoint for candidates to apply for a job or express interest.
    Accepts candidate_data as Form string (JSON serialized) and file uploads.
    """
    try:
        candidate_id = str(uuid.uuid4())

        # Parse and validate candidate_data JSON
        import json
        from pydantic import ValidationError
        try:
            data_dict = json.loads(candidate_data)
            candidate_in = ExternalCandidateCreate(**data_dict)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in candidate_data")
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

        # Save files if provided and update URLs
        import os
        from app.shared.services.file_service import save_upload

        if resume:
            stored_path, _, _ = await save_upload(resume, candidate_id)
            candidate_in.resume_url = f"/resumes/{candidate_id}/{os.path.basename(stored_path)}"
        if profile_picture:
            stored_path, _, _ = await save_upload(profile_picture, candidate_id)
            candidate_in.profile_picture_url = f"/resumes/{candidate_id}/{os.path.basename(stored_path)}"
        if salary_slip:
            stored_path, _, _ = await save_upload(salary_slip, candidate_id)
            candidate_in.salary_slip_url = f"/resumes/{candidate_id}/{os.path.basename(stored_path)}"
        if experience_letter:
            stored_path, _, _ = await save_upload(experience_letter, candidate_id)
            candidate_in.experience_letter_url = f"/resumes/{candidate_id}/{os.path.basename(stored_path)}"

        # Create new candidate record
        candidate_data_dict = candidate_in.model_dump()
        candidate_data_dict.pop("job_fair_id", None)
        candidate_data_dict.pop("job_fair_slug", None)
        candidate_data_dict.pop("agreed", None)
        db_candidate = ExternalCandidate(**candidate_data_dict)
        
        # Explicitly set generated fields to avoid None values in response
        db_candidate.id = candidate_id
        db_candidate.status = "pending"
        db_candidate.applied_at = datetime.utcnow()
        db_candidate.updated_at = datetime.utcnow()
        
        db.add(db_candidate)
        
        # Create or update corresponding User account
        user_result = await db.execute(select(User).filter(User.email == candidate_in.email))
        db_user = user_result.scalars().first()
        
        name_parts = candidate_in.full_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        dummy_password = generate_secure_password()
        hashed_pwd = hash_password(dummy_password)
        
        addr_parts = []
        if candidate_in.city:
            addr_parts.append(candidate_in.city)
        if candidate_in.state:
            addr_parts.append(candidate_in.state)
        address = ", ".join(addr_parts)
        
        first_industry = candidate_in.industries[0] if (candidate_in.industries and len(candidate_in.industries) > 0) else None
        
        is_new_user = False
        if db_user:
            # Update existing user details
            db_user.first_name = first_name
            db_user.last_name = last_name
            db_user.phone = candidate_in.phone
            db_user.is_verified = True
            db_user.gender = candidate_in.gender
            db_user.experience = candidate_in.total_experience
            db_user.address = address or db_user.address
            db_user.industry = first_industry or db_user.industry
            db_user.job_role = candidate_in.sub_role or db_user.job_role
            db_user.updated_at = datetime.utcnow()
            user_id = db_user.id
        else:
            is_new_user = True
            # Create a brand new user
            user_id = str(uuid.uuid4())
            db_user = User(
                id=user_id,
                first_name=first_name,
                last_name=last_name,
                email=candidate_in.email,
                phone=candidate_in.phone,
                hashed_password=hashed_pwd,
                role=UserRole.seeker,
                is_verified=True,
                onboarding_complete=False,
                gender=candidate_in.gender,
                experience=candidate_in.total_experience,
                address=address,
                industry=first_industry,
                job_role=candidate_in.sub_role,
                is_first_login=True
            )
            db.add(db_user)
            
        # Create ImportedUserPassword record only for brand new users
        if is_new_user:
            db_pwd = ImportedUserPassword(
                id=str(uuid.uuid4()),
                user_id=user_id,
                email=candidate_in.email,
                plain_password=dummy_password
            )
            db.add(db_pwd)
        
        # ALSO create a record in the central applications table for the provider dashboard
        # only if a specific job_id is provided. (Global leads only stay in external_candidates)
        if candidate_in.job_id:
            app_record = Application(
                id=str(uuid.uuid4()),
                job_id=candidate_in.job_id,
                seeker_id=user_id, # Link to created/updated User record
                candidate_name=candidate_in.full_name,
                candidate_email=candidate_in.email,
                candidate_phone=candidate_in.phone,
                candidate_experience=candidate_in.total_experience,
                candidate_resume_url=candidate_in.resume_url,
                status=ApplicationStatus.applied,
                applied_at=db_candidate.applied_at
            )
            db.add(app_record)
        
        # Link to Job Fair if job_fair_id or job_fair_slug is provided
        job_fair_id_to_link = candidate_in.job_fair_id
        jf_out = None
        if not job_fair_id_to_link and candidate_in.job_fair_slug:
            from app.modules.jobs_portal.services.job_fair_db import get_job_fair_db
            jf_out = await get_job_fair_db(db, candidate_in.job_fair_slug)
            if jf_out:
                job_fair_id_to_link = jf_out.id
        elif job_fair_id_to_link:
            from app.modules.jobs_portal.services.job_fair_db import get_job_fair_db
            jf_out = await get_job_fair_db(db, job_fair_id_to_link)
        
        if job_fair_id_to_link:
            from app.modules.jobs_portal.models.job_fair import JobFairSeeker
            jfs_result = await db.execute(
                select(JobFairSeeker).filter(
                    JobFairSeeker.job_fair_id == job_fair_id_to_link,
                    JobFairSeeker.seeker_id == user_id
                )
            )
            jfs = jfs_result.scalars().first()
            if not jfs:
                jfs = JobFairSeeker(
                    id=str(uuid.uuid4()),
                    job_fair_id=job_fair_id_to_link,
                    seeker_id=user_id,
                    is_attending=True,
                    registered_at=db_candidate.applied_at
                )
                db.add(jfs)
        
        await db.commit()
        await db.refresh(db_candidate)

        # Trigger welcome/credentials email for newly registered seekers
        if is_new_user:
            profile_link = f"{settings.FRONTEND_URL.rstrip('/')}/login"
            if job_fair_id_to_link:
                background_tasks.add_task(
                    send_job_fair_welcome_email,
                    candidate_in.email,
                    candidate_in.full_name,
                    dummy_password,
                    profile_link,
                    job_fair=jf_out,
                    role="seeker",
                )
            else:
                background_tasks.add_task(
                    send_welcome_email,
                    candidate_in.email,
                    first_name,
                    "seeker",
                    password=dummy_password,
                )

        # Trigger AI matching in background:
        # Find all active jobs that match this candidate's profile
        from app.modules.jobs_portal.services.external_candidate_matching_service import proactive_match_external_candidate_to_jobs
        background_tasks.add_task(proactive_match_external_candidate_to_jobs, candidate_id)
        
        return db_candidate
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/suggestions")
async def public_job_suggestions(
    type: str = Query("title"),
    q: str = Query(""),
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Autocomplete suggestions for job title or location search."""
    suggest_type = "location" if type == "location" else "title"
    return await get_job_suggestions(db, suggest_type=suggest_type, q=q, limit=limit)


@router.get("/jobs/browse-meta")
async def public_job_browse_meta(
    title_limit: int = Query(10, ge=1, le=30),
    city_limit: int = Query(12, ge=1, le=40),
    db: AsyncSession = Depends(get_db),
):
    """Popular titles and cities derived from active job postings."""
    return await get_job_browse_meta(db, title_limit=title_limit, city_limit=city_limit)


@router.get("/jobs/facets")
async def public_job_filter_facets(
    q: str | None = Query(None),
    loc: str | None = Query(None),
    exp_years: int | None = Query(None, ge=0, le=31),
    salary_min: int = Query(0, ge=0),
    salary_max: int = Query(50, ge=0),
    work_mode: str | None = Query(None),
    work_type: str | None = Query(None),
    work_shift: str | None = Query(None),
    education: str | None = Query(None),
    english: str | None = Query(None),
    gender: str | None = Query(None),
    industry: str | None = Query(None),
    date_filter: str = Query("all"),
    db: AsyncSession = Depends(get_db),
):
    """Filter option counts for public job search sidebar."""
    modes = [m.strip() for m in work_mode.split(",") if m.strip()] if work_mode else []
    types = [t.strip() for t in work_type.split(",") if t.strip()] if work_type else []
    shifts = [s.strip() for s in work_shift.split(",") if s.strip()] if work_shift else []
    edu = [e.strip() for e in education.split(",") if e.strip()] if education else []
    eng = [e.strip() for e in english.split(",") if e.strip()] if english else []
    gen = [g.strip() for g in gender.split(",") if g.strip()] if gender else []
    ind = [i.strip() for i in industry.split(",") if i.strip()] if industry else []
    return await get_job_filter_facets(
        db,
        q=q,
        loc=loc,
        exp_years=exp_years,
        salary_min=salary_min,
        salary_max=salary_max,
        work_modes=modes,
        work_types=types,
        work_shifts=shifts,
        education=edu,
        english=eng,
        gender=gen,
        industries=ind,
        date_filter=date_filter,
    )


@router.get("/jobs")
async def get_public_jobs(
    q: str | None = Query(None),
    loc: str | None = Query(None),
    exp: str | None = Query(None),
    exp_years: int | None = Query(None, ge=0, le=31),
    date_filter: str = Query("all"),
    min_salary: int = Query(0, ge=0),
    salary_min: int = Query(0, ge=0),
    salary_max: int = Query(50, ge=0),
    work_mode: str | None = Query(None),
    work_type: str | None = Query(None),
    work_shift: str | None = Query(None),
    department: str | None = Query(None),
    education: str | None = Query(None),
    english: str | None = Query(None),
    gender: str | None = Query(None),
    industry: str | None = Query(None),
    sort: str = Query("relevant"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Paginated public job search with filters."""
    modes = [m.strip() for m in work_mode.split(",") if m.strip()] if work_mode else []
    types = [t.strip() for t in work_type.split(",") if t.strip()] if work_type else []
    shifts = [s.strip() for s in work_shift.split(",") if s.strip()] if work_shift else []
    edu = [e.strip() for e in education.split(",") if e.strip()] if education else []
    eng = [e.strip() for e in english.split(",") if e.strip()] if english else []
    gen = [g.strip() for g in gender.split(",") if g.strip()] if gender else []
    ind = [i.strip() for i in industry.split(",") if i.strip()] if industry else []
    return await search_public_jobs(
        db,
        q=q,
        loc=loc,
        exp=exp,
        exp_years=exp_years,
        date_filter=date_filter,
        min_salary=min_salary,
        salary_min=salary_min,
        salary_max=salary_max,
        work_modes=modes,
        work_types=types,
        work_shifts=shifts,
        department=department,
        education=edu,
        english=eng,
        gender=gen,
        industries=ind,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}/similar")
async def get_public_job_similar(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(JobPosting)
        .options(selectinload(JobPosting.provider))
        .filter(JobPosting.id == job_id, JobPosting.is_active == True)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or inactive")
    return await get_similar_jobs(db, job)


@router.get("/jobs/{job_id}")
async def get_public_job_detail(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns detailed information for a specific job for public viewing.
    """
    result = await db.execute(
        select(JobPosting)
        .options(selectinload(JobPosting.provider))
        .filter(JobPosting.id == job_id, JobPosting.is_active == True)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or inactive")

    return serialize_public_job_detail(job)

@router.post("/parse-resume")
async def parse_resume_public(file: UploadFile = File(...)):
    """
    Public OCR/AI resume parse for job-fair / external apply auto-fill.
    Accepts PDF, DOC/DOCX, TXT, JPG/JPEG/PNG. Max size follows MAX_UPLOAD_MB.
    """
    import os
    from pathlib import Path
    from app.shared.services.file_service import save_upload, ALLOWED_EXTENSIONS
    from app.shared.services.resume_parser import parse_resume, extract_profile_fields_with_ai

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file. Upload PDF, DOC, DOCX, TXT, JPG, JPEG, or PNG.",
        )

    owner_id = f"parse_{uuid.uuid4().hex[:12]}"
    file_path = None
    try:
        file_path, original_filename, _ = await save_upload(file, owner_id)
        # Offload to a worker thread - parse_resume can fall back to synchronous
        # pytesseract OCR, which would otherwise block the whole event loop.
        raw_text, parsed_json = await asyncio.to_thread(parse_resume, file_path, original_filename)
        if not (raw_text or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from resume. Try a clearer PDF, DOCX, or image.",
            )

        ai_data: dict = {}
        try:
            ai_data = await extract_profile_fields_with_ai(raw_text, parsed_json) or {}
        except Exception:
            ai_data = {}

        full_name = (
            ai_data.get("full_name")
            or " ".join(
                p for p in [ai_data.get("first_name"), ai_data.get("last_name")] if p
            ).strip()
            or None
        )
        skills = ai_data.get("skills") or parsed_json.get("skills") or []
        if isinstance(skills, list):
            skill_names = [
                (s.get("name") if isinstance(s, dict) else str(s)) for s in skills if s
            ]
            skills_str = ", ".join(skill_names)
        else:
            skills_str = str(skills) if skills else ""

        phone = ai_data.get("phone") or parsed_json.get("phone")
        if phone:
            digits = "".join(c for c in str(phone) if c.isdigit())
            if len(digits) > 10:
                digits = digits[-10:]
            phone = digits if len(digits) == 10 else str(phone)

        exp_years = ai_data.get("total_experience_years")
        if exp_years is None:
            exp_years = parsed_json.get("experience_years")

        ocr_used = ext in {".jpg", ".jpeg", ".png"} or (
            bool(raw_text) and len(raw_text.strip()) < 300 and ext == ".pdf"
        )

        return {
            "full_name": full_name,
            "email": ai_data.get("email") or parsed_json.get("email"),
            "phone": phone,
            "date_of_birth": ai_data.get("date_of_birth"),
            "gender": ai_data.get("gender"),
            "city": ai_data.get("city"),
            "state": ai_data.get("state"),
            "qualification": ai_data.get("highest_qualification"),
            "total_experience_years": exp_years,
            "sub_role": ai_data.get("job_role") or ai_data.get("current_role"),
            "skills": skills_str,
            "ocr_used": ocr_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume parse failed: {e}") from e
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


@router.post("/upload")
async def upload_public_file(
    file: UploadFile = File(...),
    candidate_id: str = None
):
    """
    Publicly accessible endpoint to upload documents during application.
    """
    import os
    from app.shared.services.file_service import save_upload
    try:
        # If no candidate_id, we use a generic 'public' folder or generate a temp one
        owner_id = candidate_id if candidate_id else f"guest_{uuid.uuid4().hex[:8]}"
        file_path, original_filename, size_bytes = await save_upload(file, owner_id)
        
        # Use the actual filename saved on disk (safe_name)
        stored_filename = os.path.basename(file_path)
        
        # Return the relative path that the static mount expects
        # The path includes /resumes/ because save_upload adds it
        relative_path = f"/resumes/{owner_id}/{stored_filename}"
        return {"url": relative_path, "filename": original_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.put("/shortlist/{candidate_id}", response_model=ExternalCandidateOut)
# async def shortlist_candidate(candidate_id: str, db: AsyncSession = Depends(get_db)):
#     """
#     Shortlist a candidate by ID (Provider only endpoint).
#     """
#     result = await db.execute(select(ExternalCandidate).filter(ExternalCandidate.id == candidate_id))
#     candidate = result.scalar_one_or_none()
#     if not candidate:
#         raise HTTPException(status_code=404, detail="Candidate not found")
    
#     candidate.status = "shortlisted"
#     candidate.updated_at = datetime.utcnow()
    
#     await db.commit()
#     await db.refresh(candidate)
#     return candidate

@router.put("/shortlist/{candidate_id}",response_model=ExternalCandidateOut)
async def shortlist_candidate(candidate_id:str,db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(ExternalCandidate).filter(ExternalCandidate.id == candidate_id))
    print(result)
    candidate = result.scalar_one_or_none()
    print(candidate)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.status = "shortlisted"
    candidate.updated_at = datetime.utcnow();
    
    # Update corresponding Application record
    from sqlalchemy import update, and_
    if candidate.job_id:
        await db.execute(
            update(Application)
            .where(
                and_(
                    Application.candidate_email == candidate.email,
                    Application.job_id == candidate.job_id
                )
            )
            .values(status=ApplicationStatus.shortlisted)
        )
    
    await db.commit()
    await db.refresh(candidate)
    return candidate

@router.put("/reject/{candidate_id}", response_model=ExternalCandidateOut)
async def reject_candidate(candidate_id: str, db: AsyncSession = Depends(get_db)):
    """
    Reject a candidate by ID (Provider only endpoint).
    """
    result = await db.execute(select(ExternalCandidate).filter(ExternalCandidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    candidate.status = "rejected"
    candidate.updated_at = datetime.utcnow()
    
    # Update corresponding Application record
    from sqlalchemy import update, and_
    if candidate.job_id:
        await db.execute(
            update(Application)
            .where(
                and_(
                    Application.candidate_email == candidate.email,
                    Application.job_id == candidate.job_id
                )
            )
            .values(status=ApplicationStatus.rejected)
        )
        
    await db.commit()
    await db.refresh(candidate)
    return candidate


@router.get("/candidates/{candidate_id}/matches", response_model=List[ExternalCandidateMatchOut])
async def get_candidate_job_matches(candidate_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns AI-matched jobs for a specific external candidate.
    Ordered by match score descending.
    """
    result = await db.execute(
        select(ExternalCandidateMatch)
        .where(ExternalCandidateMatch.candidate_id == candidate_id)
        .order_by(ExternalCandidateMatch.score.desc())
    )
    matches = result.scalars().all()

    if not matches:
        return []

    job_ids = [m.job_id for m in matches]
    jobs_result = await db.execute(
        select(JobPosting).where(JobPosting.id.in_(job_ids), JobPosting.is_active == True)  # noqa
    )
    jobs_map = {str(j.id): j for j in jobs_result.scalars().all()}

    output = []
    for match in matches:
        job = jobs_map.get(str(match.job_id))
        if not job:
            continue
        output.append(
            ExternalCandidateMatchOut(
                match_id=match.id,
                candidate_id=match.candidate_id,
                job_id=match.job_id,
                job_title=job.title,
                job_industry=job.industry,
                job_location=job.location,
                job_experience_required=job.experience_required,
                score=match.score,
                highlights=match.highlights or [],
                gaps=match.gaps or [],
                fit_reason=match.fit_reason or "",
                created_at=match.created_at,
            )
        )
    return output


@router.get("/jobs/{job_id}/external-matches", response_model=List[dict])
async def get_job_external_candidate_matches(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns AI-matched external candidates for a specific job posting.
    Ordered by match score descending. Intended for provider dashboard.
    """
    from datetime import timedelta

    # Verify job exists
    job_result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(ExternalCandidateMatch)
        .where(ExternalCandidateMatch.job_id == job_id)
        .order_by(ExternalCandidateMatch.score.desc())
    )
    matches = result.scalars().all()

    if not matches:
        return []

    # Window for "new match" flag
    ten_min_ago = datetime.utcnow() - timedelta(minutes=10)

    candidate_ids = [m.candidate_id for m in matches]
    candidates_result = await db.execute(
        select(ExternalCandidate).where(ExternalCandidate.id.in_(candidate_ids))
    )
    candidates_map = {str(c.id): c for c in candidates_result.scalars().all()}

    output = []
    for match in matches:
        candidate = candidates_map.get(str(match.candidate_id))
        if not candidate:
            continue
        output.append({
            "match_id": match.id,
            "candidate_id": match.candidate_id,
            "full_name": candidate.full_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "current_designation": candidate.current_designation,
            "sub_role": candidate.sub_role,
            "total_experience": candidate.total_experience,
            "industries": candidate.industries,
            "resume_url": candidate.resume_url,
            "status": candidate.status,
            "score": match.score,
            "highlights": match.highlights or [],
            "gaps": match.gaps or [],
            "fit_reason": match.fit_reason or "",
            "is_new_match": (
                match.created_at.replace(tzinfo=None) >= ten_min_ago
                if match.created_at else False
            ),
            "matched_at": match.created_at.isoformat() if match.created_at else None,
        })
    return output