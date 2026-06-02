from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.user import User
from models.ai_coach import AICoachSession
from services.auth_service import require_seeker
from services.ai_coach_service import AICoachService
from typing import Optional

router = APIRouter(prefix="/ai-coach", tags=["AI Coach"])

@router.post("/start")
async def start_coach_session(
    target_role: str = Body(...),
    experience_level: str = Body(...),
    focus_area: str = Body("General"),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    try:
        session = await AICoachService.initialize_session(
            db=db,
            seeker_id=user.id,
            target_role=target_role,
            experience_level=experience_level,
            focus_area=focus_area
        )
        first_question = await AICoachService.get_next_question(db, session.id)
        return {
            "session_id": session.id,
            "question": first_question
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/respond")
async def respond_to_coach(
    session_id: str = Body(...),
    answer: str = Body(...),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Verify ownership
        result = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session or session.seeker_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        next_question = await AICoachService.get_next_question(db, session_id, answer)
        return {
            "question": next_question
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{session_id}")
async def get_coach_result(
    session_id: str,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session or session.seeker_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "id": session.id,
        "target_role": session.target_role,
        "experience_level": session.experience_level,
        "focus_area": session.focus_area,
        "status": session.status,
        "overall_score": session.overall_score,
        "content_score": session.content_score,
        "communication_score": session.communication_score,
        "general_feedback": session.general_feedback,
        "strengths": session.strengths,
        "gaps": session.gaps,
        "improvement_steps": session.improvement_steps,
        "video_feedback": session.video_feedback,
        "chat_history": session.chat_history,
        "created_at": session.created_at
    }

@router.get("/sessions/me")
async def get_my_coach_sessions(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AICoachSession)
        .where(AICoachSession.seeker_id == user.id)
        .order_by(AICoachSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "target_role": s.target_role,
            "experience_level": s.experience_level,
            "focus_area": s.focus_area,
            "status": s.status,
            "overall_score": s.overall_score,
            "created_at": s.created_at
        }
        for s in sessions
    ]
