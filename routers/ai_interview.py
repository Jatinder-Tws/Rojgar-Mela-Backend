from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from services.ai_interview_service import AIInterviewService
from typing import Optional
from models.ai_interview import AIInterviewSession

router = APIRouter(prefix="/interviews/ai", tags=["AI Interview"])

@router.post("/start")
async def start_interview(
    application_id: str = Body(...),
    seeker_id: str = Body(...),
    job_id: str = Body(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        session = await AIInterviewService.initialize_session(db, application_id, seeker_id, job_id)
        first_question = await AIInterviewService.get_next_question(db, session.id)
        return {
            "session_id": session.id,
            "question": first_question
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/respond")
async def respond_to_interview(
    session_id: str = Body(...),
    answer: str = Body(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        next_question = await AIInterviewService.get_next_question(db, session_id, answer)
        return {
            "question": next_question
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{session_id}")
async def get_interview_result(session_id: str, db: AsyncSession = Depends(get_db)):
    # session_id could either be the AIInterviewSession ID or the application_id.
    result = await db.execute(select(AIInterviewSession).where(AIInterviewSession.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        # Fallback in case frontend is passing application_id instead
        result = await db.execute(select(AIInterviewSession).where(AIInterviewSession.application_id == session_id))
        session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "status": session.status,
        "score": session.score,
        "feedback": session.feedback,
        "transcript": session.chat_history
    }
