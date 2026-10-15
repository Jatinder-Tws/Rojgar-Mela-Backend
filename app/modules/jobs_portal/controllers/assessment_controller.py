"""
Assessment controller – business logic from routers/assessment.py
"""
import json as _json
import asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.models.assessment import AssessmentSession, AssessmentResult
from app.shared.models.user import User, UserRole
from app.modules.jobs_portal.schemas.assessment import AssessmentStart, AssessmentAnswer, AssessmentComplete
from app.shared.schemas.auth import LoginResponse, UserOut
from app.core.dependencies import hash_password
from app.modules.jobs_portal.services.assessment_questions import build_assessment_evaluation
from app.modules.jobs_portal.services.ai_service import (
    generate_career_evaluation,
    generate_career_question_set,
)

COST_PER_TOKEN = 0.00035 / 1000


async def _user_by_phone(phone: str, db: AsyncSession) -> User | None:
    """Return the newest account for this phone.

    Some phones were saved more than once. scalar_one_or_none raises in that
    case and the assessment finish step fails before details are saved.
    """
    result = await db.execute(
        select(User).where(User.phone == phone).order_by(User.created_at.desc())
    )
    return result.scalars().first()


async def _ensure_question_plan(session) -> list:
    plan = session.question_plan or []
    if isinstance(plan, list) and plan:
        return plan
    plan, tokens = await generate_career_question_set(session.experience_level, session.domain_interest)
    session.question_plan = plan
    session.tokens_utilized = (session.tokens_utilized or 0) + (tokens or 0)
    session.cost = (session.cost or 0) + (tokens or 0) * COST_PER_TOKEN
    return plan


def _question_payload(plan: list, index: int) -> dict:
    if index >= len(plan):
        return {"is_complete": True}
    item = plan[index] or {}
    return {
        "question": item.get("question"),
        "options": item.get("options") or [],
        "category": item.get("category") or "",
        "total": len(plan),
        "is_complete": False,
    }


async def _score_session(session) -> dict:
    try:
        return await generate_career_evaluation(
            session.qa_history, session.experience_level, session.domain_interest
        )
    except Exception as exc:
        print(f"Career evaluation fallback: {exc}")
        return build_assessment_evaluation(
            session.qa_history, session.experience_level, session.domain_interest
        )


async def start_assessment(body: AssessmentStart, db: AsyncSession) -> AssessmentSession:
    session = AssessmentSession(
        experience_level=(body.experience_level or "")[:100],
        domain_interest=(body.domain_interest or "")[:255],
        qa_history=[]
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_next_question(session_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(AssessmentSession).where(AssessmentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    plan = await _ensure_question_plan(session)
    await db.commit()
    index = len(session.qa_history or [])
    if index >= len(plan):
        return {"is_complete": True}
    return _question_payload(plan, index)


async def submit_answer(session_id: str, body: AssessmentAnswer, db: AsyncSession) -> dict:
    result = await db.execute(select(AssessmentSession).where(AssessmentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    new_history = list(session.qa_history) if session.qa_history else []
    new_history.append({"question": body.question, "answer": body.answer})
    plan = await _ensure_question_plan(session)
    answered_index = len(new_history) - 1
    if 0 <= answered_index < len(plan):
        new_history[-1]["category"] = (plan[answered_index] or {}).get("category") or ""
    session.qa_history = new_history
    if len(new_history) >= len(plan):
        session.status = "completed"
        await db.commit()
        await db.refresh(session)
        return {"is_complete": True, "total": len(plan)}
    await db.commit()
    return _question_payload(plan, len(new_history))
async def complete_assessment(session_id: str, body: AssessmentComplete, db: AsyncSession) -> LoginResponse:
    result = await db.execute(select(AssessmentSession).where(AssessmentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user = await _user_by_phone(body.phone, db)
    existing_account = user is not None
    if not user:
        if body.email:
            email_result = await db.execute(select(User).where(User.email == body.email))
            email_user = email_result.scalar_one_or_none()
            if email_user:
                raise HTTPException(status_code=400, detail="Email already registered")
        user = User(
            email=body.email, phone=body.phone, first_name=body.first_name, last_name=body.last_name,
            role=UserRole(body.role) if body.role else UserRole.seeker,
            is_verified=False, onboarding_complete=False, is_assessment_done=True
        )
        if body.password:
            user.hashed_password = hash_password(body.password)
        db.add(user)
        await db.flush()
    else:
        user.is_assessment_done = True

    # Check if AssessmentResult already exists
    res_query = await db.execute(select(AssessmentResult).where(AssessmentResult.session_id == session_id))
    assessment_result = res_query.scalar_one_or_none()
    if assessment_result:
        if assessment_result.user_id is None:
            assessment_result.user_id = user.id
            db.add(assessment_result)
    else:
        eval_data = await _score_session(session)
        eval_tokens = eval_data.get("tokens_utilized", 0)
        session.tokens_utilized = (session.tokens_utilized or 0) + eval_tokens
        session.cost = (session.cost or 0) + eval_tokens * COST_PER_TOKEN
        db.add(session)
        assessment_result = AssessmentResult(
            session_id=session.id, user_id=user.id,
            personality_type=eval_data["personality_type"], iq_score=eval_data["iq_estimate"],
            aptitude_score=eval_data.get("aptitude_score"), reasoning_score=eval_data.get("reasoning_score"),
            emotional_intelligence_score=eval_data.get("emotional_intelligence_score"),
            personality_score=eval_data.get("personality_score"),
            recommended_domains=eval_data["recommended_domains"], detailed_evaluation=eval_data["detailed_evaluation"],
            tokens_utilized=session.tokens_utilized, cost=session.cost
        )
        db.add(assessment_result)
    await db.commit()
    await db.refresh(user)
    return LoginResponse(
        message="Assessment saved on your existing account." if existing_account else "Assessment complete.",
        linked=existing_account,
        requires_setup=False,
        user=UserOut.model_validate(user),
    )


async def get_result(session_id: str, db: AsyncSession) -> AssessmentResult:
    result = await db.execute(select(AssessmentResult).where(AssessmentResult.session_id == session_id))
    assessment_result = result.scalar_one_or_none()
    if not assessment_result:
        # Check if AssessmentSession exists and has history
        sess_res = await db.execute(select(AssessmentSession).where(AssessmentSession.id == session_id))
        session = sess_res.scalar_one_or_none()
        if not session or not session.qa_history:
            raise HTTPException(status_code=404, detail="Result not found")
        
        # Dynamically generate the result!
        eval_data = await _score_session(session)
        eval_tokens = eval_data.get("tokens_utilized", 0)
        session.tokens_utilized = (session.tokens_utilized or 0) + eval_tokens
        session.cost = (session.cost or 0) + eval_tokens * COST_PER_TOKEN
        session.status = "completed"
        db.add(session)
        
        assessment_result = AssessmentResult(
            session_id=session.id,
            user_id=None,
            personality_type=eval_data["personality_type"],
            iq_score=eval_data["iq_estimate"],
            aptitude_score=eval_data.get("aptitude_score"),
            reasoning_score=eval_data.get("reasoning_score"),
            emotional_intelligence_score=eval_data.get("emotional_intelligence_score"),
            personality_score=eval_data.get("personality_score"),
            recommended_domains=eval_data["recommended_domains"],
            detailed_evaluation=eval_data["detailed_evaluation"],
            tokens_utilized=session.tokens_utilized,
            cost=session.cost
        )
        db.add(assessment_result)
        await db.commit()
        await db.refresh(assessment_result)
        
    return assessment_result


async def check_phone(phone: str, db: AsyncSession) -> dict:
    user = await _user_by_phone(phone, db)
    if user:
        return {"exists": True, "first_name": user.first_name, "last_name": user.last_name, "email": user.email}
    return {"exists": False}


async def get_by_user(user_id: str, db: AsyncSession):
    result = await db.execute(select(AssessmentResult).where(AssessmentResult.user_id == user_id))
    return result.scalar_one_or_none()


async def link_to_profile(session_id: str, user: User, db: AsyncSession) -> dict:
    result = await db.execute(select(AssessmentResult).where(AssessmentResult.session_id == session_id))
    assessment_result = result.scalar_one_or_none()
    if not assessment_result:
        sess_res = await db.execute(select(AssessmentSession).where(AssessmentSession.id == session_id))
        session = sess_res.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        eval_data = await _score_session(session)
        eval_tokens = eval_data.get("tokens_utilized", 0)
        session.tokens_utilized = (session.tokens_utilized or 0) + eval_tokens
        session.cost = (session.cost or 0) + eval_tokens * COST_PER_TOKEN
        db.add(session)
        assessment_result = AssessmentResult(
            session_id=session.id, user_id=user.id,
            personality_type=eval_data["personality_type"], iq_score=eval_data["iq_estimate"],
            aptitude_score=eval_data.get("aptitude_score"), reasoning_score=eval_data.get("reasoning_score"),
            emotional_intelligence_score=eval_data.get("emotional_intelligence_score"),
            personality_score=eval_data.get("personality_score"),
            recommended_domains=eval_data["recommended_domains"], detailed_evaluation=eval_data["detailed_evaluation"],
            tokens_utilized=session.tokens_utilized, cost=session.cost
        )
        db.add(assessment_result)
    else:
        if assessment_result.user_id is None:
            assessment_result.user_id = user.id
        elif assessment_result.user_id != user.id:
            raise HTTPException(status_code=403, detail="Assessment already linked to another user")
    user.is_assessment_done = True
    await db.commit()
    return {"message": "Linked successfully"}


async def get_my_assessment(user: User, db: AsyncSession):
    result = await db.execute(select(AssessmentResult).where(AssessmentResult.user_id == user.id))
    return result.scalar_one_or_none()
