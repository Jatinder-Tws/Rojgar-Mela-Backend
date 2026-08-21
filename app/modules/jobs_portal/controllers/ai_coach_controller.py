"""
AI Coach controller – business logic for AI Coach interview sessions and credit system.
Strictly enforced for Job Seekers only.
"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.models.ai_coach import AICoachSession
from app.shared.models.user import User
from app.modules.jobs_portal.services.ai_coach_service import AICoachService
from app.modules.jobs_portal.services.ai_coach_credits_service import AICoachCreditsService


async def get_credit_balance(user: User, db: AsyncSession) -> dict:
    AICoachCreditsService.verify_seeker_role(user)
    account = await AICoachCreditsService.get_or_create_account(db, user)
    return {
        "balance": account.balance,
        "total_earned": account.total_earned,
        "total_spent": account.total_spent
    }


async def start_coach_session(
    target_role: str,
    experience_level: str,
    focus_area: str,
    user: User,
    db: AsyncSession,
) -> dict:
    AICoachCreditsService.verify_seeker_role(user)
    
    # Check minimum 1 credit requirement
    account = await AICoachCreditsService.get_or_create_account(db, user)
    if account.balance < 1:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits. Minimum 1 credit required to start an interview practice session."
        )
        
    try:
        session = await AICoachService.initialize_session(
            db=db, seeker_id=user.id, target_role=target_role,
            experience_level=experience_level, focus_area=focus_area,
        )
        first_res = await AICoachService.get_next_question(db, session.id)
        return {
            "session_id": session.id,
            "question": first_res["message"],
            "rating": first_res.get("rating"),
            "feedback": first_res.get("feedback"),
            "credits_remaining": account.balance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def start_live_coach_session(
    target_role: str,
    experience_level: str,
    focus_area: str,
    user: User,
    db: AsyncSession,
) -> dict:
    """Creates a session for the Gemini Live voice interview mode. Unlike
    start_coach_session, does not call get_next_question - Gemini Live asks the
    questions itself once the caller opens the /ws/ai-coach-live/{session_id} socket."""
    AICoachCreditsService.verify_seeker_role(user)

    account = await AICoachCreditsService.get_or_create_account(db, user)
    if account.balance < 1:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits. Minimum 1 credit required to start an interview practice session."
        )

    session = await AICoachService.initialize_session(
        db=db, seeker_id=user.id, target_role=target_role,
        experience_level=experience_level, focus_area=focus_area,
    )
    session.mode = "live"
    await db.commit()

    return {
        "session_id": session.id,
        "credits_remaining": account.balance,
    }


async def process_heartbeat(session_id: str, user: User, db: AsyncSession) -> dict:
    AICoachCreditsService.verify_seeker_role(user)
    success, remaining = await AICoachCreditsService.deduct_heartbeat_credit(db, user, session_id)
    if not success:
        return {
            "status": "depleted",
            "credits_remaining": 0,
            "message": "Interview credits depleted. Top up to continue."
        }
    return {
        "status": "ok",
        "credits_remaining": remaining
    }


async def respond_to_coach(session_id: str, answer: str, user: User, db: AsyncSession) -> dict:
    AICoachCreditsService.verify_seeker_role(user)
    try:
        result = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session or session.seeker_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")
            
        res = await AICoachService.get_next_question(db, session_id, answer)
        return {
            "question": res["message"],
            "message": res["message"],
            "rating": res.get("rating"),
            "feedback": res.get("feedback"),
            "ideal_answer": res.get("ideal_answer"),
            "answer_to_user_query": res.get("answer_to_user_query"),
            "is_wrapup": res.get("is_wrapup", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def create_credit_order(package_id: str, user: User, db: AsyncSession) -> dict:
    AICoachCreditsService.verify_seeker_role(user)
    return await AICoachCreditsService.create_purchase_order(db, user, package_id)


async def verify_credit_order(
    provider_order_id: str, provider_payment_id: str, provider_signature: str, user: User, db: AsyncSession
) -> dict:
    AICoachCreditsService.verify_seeker_role(user)
    return await AICoachCreditsService.verify_and_fulfill_order(
        db, user, provider_order_id, provider_payment_id, provider_signature
    )


async def get_active_room_session(session_id: str, user: User, db: AsyncSession) -> dict:
    AICoachCreditsService.verify_seeker_role(user)
    return await AICoachService.get_active_room_session(db, session_id, user.id)


async def get_coach_result(session_id: str, user: User, db: AsyncSession) -> dict:
    AICoachCreditsService.verify_seeker_role(user)
    result = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session or session.seeker_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id, "target_role": session.target_role,
        "experience_level": session.experience_level, "focus_area": session.focus_area,
        "mode": getattr(session, "mode", "text"),
        "status": session.status, "overall_score": session.overall_score,
        "content_score": session.content_score, "communication_score": session.communication_score,
        "general_feedback": session.general_feedback, "strengths": session.strengths,
        "gaps": session.gaps, "improvement_steps": session.improvement_steps,
        "video_feedback": session.video_feedback, "chat_history": session.chat_history,
        "created_at": session.created_at,
    }


async def get_my_coach_sessions(user: User, db: AsyncSession) -> list:
    AICoachCreditsService.verify_seeker_role(user)
    result = await db.execute(
        select(AICoachSession).where(AICoachSession.seeker_id == user.id).order_by(AICoachSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {"id": s.id, "target_role": s.target_role, "experience_level": s.experience_level,
         "focus_area": s.focus_area, "mode": getattr(s, "mode", "text"), "status": s.status, "overall_score": s.overall_score, "created_at": s.created_at}
        for s in sessions
    ]
