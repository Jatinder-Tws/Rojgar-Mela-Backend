import asyncio
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.job import JobPosting
from models.match import Match
from models.resume import Resume
from models.user import User
from models.notification import NotificationType
from schemas.jobs import JobWithMatch, MatchedCandidateOut
from services.notification_service import create_notification


async def get_matched_jobs(user: User, db: AsyncSession) -> List[JobWithMatch]:
    query = (
        select(JobPosting, Match.score, Match.fit_reason, Match.highlights, Match.gaps)
        .join(Match, JobPosting.id == Match.job_id)
        .where(Match.seeker_id == user.id, JobPosting.is_active == True)
        .order_by(Match.score.desc())
        .limit(50)
    )
    result = await db.execute(query)
    rows = result.all()

    results = []
    for job, score, fit_reason, highlights, gaps in rows:
        results.append(JobWithMatch(
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
            match_score=score,
            highlights=highlights,
            gaps=gaps,
            fit_reason=fit_reason,
            ai_interview_enabled=job.ai_interview_enabled,
            selection_threshold=job.selection_threshold,
        ))
    return results


async def get_matched_candidates(
    job_id: Optional[str],
    all_jobs: bool,
    user: User,
    db: AsyncSession,
) -> List[MatchedCandidateOut]:
    if all_jobs:
        # Fetch matches for all of the provider's active jobs
        jobs_res = await db.execute(
            select(JobPosting.id).where(JobPosting.provider_id == user.id, JobPosting.is_active == True)
        )
        job_ids = [row[0] for row in jobs_res.all()]
        if not job_ids:
            return []
        
        matches_result = await db.execute(
            select(Match).where(Match.job_id.in_(job_ids)).order_by(Match.score.desc()).limit(100)
        )
        matches = matches_result.scalars().all()
    elif job_id:
        result = await db.execute(
            select(JobPosting).where(JobPosting.id == job_id, JobPosting.provider_id == user.id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        matches_result = await db.execute(
            select(Match).where(Match.job_id == job.id).order_by(Match.score.desc()).limit(100)
        )
        matches = matches_result.scalars().all()
    else:
        result = await db.execute(
            select(JobPosting)
            .where(JobPosting.provider_id == user.id, JobPosting.is_active == True)  # noqa
            .order_by(JobPosting.created_at.desc())
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="No active job postings found")
        
        matches_result = await db.execute(
            select(Match).where(Match.job_id == job.id).order_by(Match.score.desc()).limit(100)
        )
        matches = matches_result.scalars().all()

    if not matches:
        return []

    seeker_ids = [m.seeker_id for m in matches]

    seekers_task = db.execute(select(User).where(User.id.in_(seeker_ids)))
    resumes_task = db.execute(
        select(Resume).where(Resume.user_id.in_(seeker_ids)).order_by(Resume.created_at.desc())
    )

    seekers_res, resumes_res = await asyncio.gather(seekers_task, resumes_task)

    seekers_map = {str(u.id): u for u in seekers_res.scalars().all()}

    resumes_map = {}
    for resume in resumes_res.scalars().all():
        if str(resume.user_id) not in resumes_map:
            resumes_map[str(resume.user_id)] = resume

    results = []
    for match in matches:
        seeker = seekers_map.get(str(match.seeker_id))
        if not seeker:
            continue
        resume = resumes_map.get(str(match.seeker_id))
        results.append(MatchedCandidateOut(
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
            job_id=str(match.job_id),
        ))
    return results


async def get_candidate_by_match(match_id: str, user: User, db: AsyncSession) -> MatchedCandidateOut:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    job_result = await db.execute(select(JobPosting).where(JobPosting.id == match.job_id))
    job = job_result.scalar_one_or_none()
    if not job or job.provider_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this candidate")

    seeker_result = await db.execute(select(User).where(User.id == match.seeker_id))
    seeker = seeker_result.scalar_one_or_none()
    if not seeker:
        raise HTTPException(status_code=404, detail="Candidate not found")

    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == match.seeker_id).order_by(Resume.created_at.desc()).limit(1)
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


async def show_interest(candidate_id: str, user: User, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.id == candidate_id))
    candidate = result.scalar_one_or_none()
    role_str = (candidate.role.value if candidate and hasattr(candidate.role, "value") else str(candidate.role)) if candidate else None
    if not candidate or role_str != "seeker":
        raise HTTPException(status_code=404, detail="Candidate not found")

    await create_notification(
        db=db,
        user_id=candidate_id,
        type=NotificationType.interest,
        title="Profile Interest:",
        message=f"{user.first_name} {user.last_name} from {user.company_name or 'a company'} has shown interest in your profile. Log in to view and connect.",
        related_user_id=user.id,
    )
    return {"message": "Interest shown successfully. Candidate has been notified."}
