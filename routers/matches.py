from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.job import JobPosting
from models.user import User
from models.match import Match
from models.notification import Notification, NotificationType
from schemas.jobs import JobWithMatch, MatchedCandidateOut
from services.auth_service import require_seeker, require_provider, require_verified
from services.seeker_matching_service import match_jobs_for_seeker, match_candidates_for_job
from services.notification_service import create_notification

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/jobs", response_model=List[JobWithMatch])
async def get_matched_jobs(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    """Seeker: get AI-matched job recommendations from pre-computed matches."""
    # Fetch matches from database (already computed during resume upload)
    matches_result = await db.execute(
        select(Match)
        .where(Match.seeker_id == user.id)
        .order_by(Match.score.desc())
        .limit(50)
    )
    matches = matches_result.scalars().all()

    if not matches:
        return []

    # Get job details for all matches
    job_ids = [m.job_id for m in matches]
    jobs_result = await db.execute(
        select(JobPosting).where(
            JobPosting.id.in_(job_ids), JobPosting.is_active == True
        )  # noqa
    )
    jobs_map = {str(j.id): j for j in jobs_result.scalars().all()}

    # Build response
    results = []
    for match in matches:
        job = jobs_map.get(str(match.job_id))
        if not job:
            continue

        results.append(
                JobWithMatch(
                    id=str(job.id),
                    provider_id=str(job.provider_id),
                    title=job.title,
                    description=job.description,
                    required_skills=job.required_skills or [],
                    salary_range=job.salary_range,
                    job_type=str(job.job_type.value) if hasattr(job.job_type, "value") else job.job_type,
                    industry=job.industry,
                    posted_by_name=job.posted_by_name,
                    experience_required=job.experience_required,
                    location=job.location,
                    is_active=job.is_active,
                    created_at=job.created_at,
                    post_count=job.post_count,
                    match_score=match.score,
                    highlights=match.highlights,
                    gaps=match.gaps,
                    fit_reason=match.fit_reason,
                    ai_interview_enabled=job.ai_interview_enabled,
                    selection_threshold=job.selection_threshold,
                )
        )

    return results


@router.get("/candidates", response_model=List[MatchedCandidateOut])
async def get_matched_candidates(
    job_id: Optional[str] = Query(None, description="Filter by specific job posting"),
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    """Provider: get AI-matched candidates from pre-computed matches."""
    # Determine which job to show matches for
    if job_id:
        result = await db.execute(
            select(JobPosting).where(
                JobPosting.id == job_id, JobPosting.provider_id == user.id
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    else:
        # No job_id → use most recent active job
        result = await db.execute(
            select(JobPosting)
            .where(JobPosting.provider_id == user.id, JobPosting.is_active == True)  # noqa
            .order_by(JobPosting.created_at.desc())
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="No active job postings found")

    # Fetch matches from database (already computed during job posting)
    from models.resume import Resume

    matches_result = await db.execute(
        select(Match)
        .where(Match.job_id == job.id)
        .order_by(Match.score.desc())
        .limit(100)
    )
    matches = matches_result.scalars().all()


    if not matches:
        return []

    # Get seeker and resume details for all matches
    seeker_ids = [m.seeker_id for m in matches]
    seekers_result = await db.execute(select(User).where(User.id.in_(seeker_ids)))
    seekers_map = {str(u.id): u for u in seekers_result.scalars().all()}

    resumes_result = await db.execute(
        select(Resume)
        .where(Resume.user_id.in_(seeker_ids))
        .order_by(Resume.created_at.desc())
    )
    resumes_map = {}
    for resume in resumes_result.scalars().all():
        if str(resume.user_id) not in resumes_map:
            resumes_map[str(resume.user_id)] = resume

    # Build response
    results = []
    for match in matches:
        seeker = seekers_map.get(str(match.seeker_id))
        if not seeker:
            continue

        resume = resumes_map.get(str(match.seeker_id))

        results.append(
            MatchedCandidateOut(
                match_id=str(match.id),
                user_id=str(seeker.id),
                first_name=seeker.first_name,
                last_name=seeker.last_name,
                email=seeker.email,
                score=match.score,
                highlights=match.highlights,
                gaps=match.gaps,
                fit_reason=match.fit_reason,
                resume_parsed_json=resume.parsed_json if resume else None,
                resume_filename=resume.filename if resume else None,
                profile_pic_url=seeker.profile_pic_url,
            )
        )

    return results


@router.get("/candidate/{match_id}", response_model=MatchedCandidateOut)
async def get_candidate_by_match(
    match_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    """Provider: get detailed candidate profile by match_id."""
    from models.match import Match
    from models.resume import Resume

    # Fetch the match record
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Verify the job belongs to this provider
    job_result = await db.execute(
        select(JobPosting).where(JobPosting.id == match.job_id)
    )
    job = job_result.scalar_one_or_none()
    if not job or job.provider_id != user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this candidate"
        )

    # Get seeker details
    seeker_result = await db.execute(select(User).where(User.id == match.seeker_id))
    seeker = seeker_result.scalar_one_or_none()
    if not seeker:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get resume
    resume_result = await db.execute(
        select(Resume)
        .where(Resume.user_id == match.seeker_id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume = resume_result.scalar_one_or_none()

    return MatchedCandidateOut(
        match_id=match.id,
        user_id=seeker.id,
        first_name=seeker.first_name,
        last_name=seeker.last_name,
        email=seeker.email,
        score=match.score,
        highlights=match.highlights,
        gaps=match.gaps,
        fit_reason=match.fit_reason,
        resume_parsed_json=resume.parsed_json if resume else None,
        resume_filename=resume.filename if resume else None,
        profile_pic_url=seeker.profile_pic_url,
    )


@router.post("/interest/{candidate_id}", status_code=200)
async def show_interest(
    candidate_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    """Provider shows interest in a candidate profile → sends notification to seeker."""
    # Verify candidate exists
    result = await db.execute(select(User).where(User.id == candidate_id))
    candidate = result.scalar_one_or_none()

    role_str = (
        candidate.role.value
        if candidate and hasattr(candidate.role, "value")
        else str(candidate.role)
    )
    if not candidate or role_str != "seeker":
        raise HTTPException(status_code=404, detail="Candidate not found")

    await create_notification(
        db=db,
        user_id=candidate_id,
        type=NotificationType.interest,
        title="A recruiter is interested in your profile! 👀",
        message=f"{user.first_name} {user.last_name} from {user.company_name or 'a company'} has shown interest in your profile. Log in to view and connect.",
        related_user_id=user.id,
    )
    return {"message": "Interest shown successfully. Candidate has been notified."}


@router.get("/seeker")
async def get_seeker_matches_alias(
    user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)
):
    return await get_matched_jobs(user, db)


@router.get("/job/{job_id}")
async def get_job_matches_alias(
    job_id: str,
    user: User = Depends(require_provider),
    db: AsyncSession = Depends(get_db),
):
    return await get_matched_candidates(job_id, user, db)
