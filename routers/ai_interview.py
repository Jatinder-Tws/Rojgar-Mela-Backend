from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from controllers.ai_interview_controller import (
    start_interview as ctrl_start_interview,
    respond_to_interview as ctrl_respond_to_interview,
    get_interview_result as ctrl_get_interview_result,
)

router = APIRouter(prefix="/interviews/ai", tags=["AI Interview"])


@router.post("/start")
async def start_interview(
    application_id: str = Body(...),
    seeker_id: str = Body(...),
    job_id: str = Body(...),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_start_interview(application_id, seeker_id, job_id, db)


@router.post("/respond")
async def respond_to_interview(
    session_id: str = Body(...),
    answer: str = Body(...),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_respond_to_interview(session_id, answer, db)


@router.get("/result/{session_id}")
async def get_interview_result(session_id: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_get_interview_result(session_id, db)
