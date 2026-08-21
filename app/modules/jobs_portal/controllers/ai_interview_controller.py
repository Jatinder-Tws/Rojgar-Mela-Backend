"""
AI Interview controller – business logic from routers/ai_interview.py
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.models.ai_interview import AIInterviewSession
from app.modules.jobs_portal.services.ai_interview_service import AIInterviewService


async def start_interview(application_id: str, seeker_id: str, job_id: str, db: AsyncSession) -> dict:
    try:
        session = await AIInterviewService.initialize_session(db, application_id, seeker_id, job_id)
        first_question = await AIInterviewService.get_next_question(db, session.id)
        return {"session_id": session.id, "question": first_question}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def respond_to_interview(session_id: str, answer: str, db: AsyncSession) -> dict:
    try:
        next_question = await AIInterviewService.get_next_question(db, session_id, answer)
        return {"question": next_question}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_interview_result(session_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(AIInterviewSession).where(AIInterviewSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        result = await db.execute(select(AIInterviewSession).where(AIInterviewSession.application_id == session_id))
        session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": session.status, "score": session.score, "feedback": session.feedback, "transcript": session.chat_history}
