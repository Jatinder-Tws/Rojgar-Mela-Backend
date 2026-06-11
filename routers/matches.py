from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.jobs import JobWithMatch, MatchedCandidateOut
from services.auth_service import require_seeker, require_provider, require_verified
from controllers.matches_controller import (
    get_matched_jobs as ctrl_get_matched_jobs,
    get_matched_candidates as ctrl_get_matched_candidates,
    get_candidate_by_match as ctrl_get_candidate_by_match,
    show_interest as ctrl_show_interest,
)

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/jobs", response_model=List[JobWithMatch])
async def get_matched_jobs(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_matched_jobs(user, db)


@router.get("/candidates", response_model=List[MatchedCandidateOut])
async def get_matched_candidates(job_id: Optional[str] = Query(None), user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_matched_candidates(job_id, user, db)


@router.get("/candidate/{match_id}", response_model=MatchedCandidateOut)
async def get_candidate_by_match(match_id: str, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_candidate_by_match(match_id, user, db)


@router.post("/interest/{candidate_id}", status_code=200)
async def show_interest(candidate_id: str, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_show_interest(candidate_id, user, db)


@router.get("/seeker")
async def get_seeker_matches_alias(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_matched_jobs(user, db)


@router.get("/job/{job_id}")
async def get_job_matches_alias(job_id: str, user: User = Depends(require_provider), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_matched_candidates(job_id, user, db)
