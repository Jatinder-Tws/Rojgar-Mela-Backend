"""
Assessment controller – business logic from routers/assessment.py
"""
import json as _json
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.assessment import AssessmentSession, AssessmentResult
from models.user import User, UserRole
from schemas.assessment import AssessmentStart, AssessmentAnswer, AssessmentComplete
from schemas.auth import LoginResponse, UserOut
from services.auth_service import create_access_token, hash_password
from services.ai_service import generate_next_assessment_question, generate_assessment_evaluation
from services.totp_service import totp_service

COST_PER_TOKEN = 0.00035 / 1000


async def start_assessment(body: AssessmentStart, db: AsyncSession) -> AssessmentSession:
    session = AssessmentSession(
        experience_level=body.experience_level,
        domain_interest=body.domain_interest,
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
    is_complete = len(session.qa_history or []) >= 15
    if is_complete:
        return {"is_complete": True}
    question_json, tokens = await generate_next_assessment_question(session.qa_history, session.experience_level, session.domain_interest)
    if isinstance(question_json, list):
        question_json = question_json[0] if question_json else {"question": "", "options": []}
    session.tokens_utilized = (session.tokens_utilized or 0) + tokens
    session.cost = (session.cost or 0) + tokens * COST_PER_TOKEN
    await db.commit()
    return {"question": question_json.get("question"), "options": question_json.get("options"), "is_complete": False}


async def submit_answer(session_id: str, body: AssessmentAnswer, db: AsyncSession) -> dict:
    result = await db.execute(select(AssessmentSession).where(AssessmentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    new_history = list(session.qa_history) if session.qa_history else []
    new_history.append({"question": body.question, "answer": body.answer})
    session.qa_history = new_history
    is_complete = len(new_history) >= 15
    if is_complete:
        session.status = "completed"
        await db.commit()
        await db.refresh(session)
        return {"is_complete": True}
    question_json, tokens = await generate_next_assessment_question(session.qa_history, session.experience_level, session.domain_interest)
    if isinstance(question_json, list):
        question_json = question_json[0] if question_json else {"question": "", "options": []}
    session.tokens_utilized = (session.tokens_utilized or 0) + tokens
    session.cost = (session.cost or 0) + tokens * COST_PER_TOKEN
    await db.commit()
    return {"question": question_json.get("question"), "options": question_json.get("options"), "is_complete": False}
async def complete_assessment(session_id: str, body: AssessmentComplete, db: AsyncSession) -> LoginResponse:
    result = await db.execute(select(AssessmentSession).where(AssessmentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user_result = await db.execute(select(User).where(User.phone == body.phone))
    user = user_result.scalar_one_or_none()
    if not user:
        if body.email:
            email_result = await db.execute(select(User).where(User.email == body.email))
            email_user = email_result.scalar_one_or_none()
            if email_user:
                raise HTTPException(status_code=400, detail="Email already registered")
        secret = totp_service.generate_secret()
        user = User(
            email=body.email, phone=body.phone, first_name=body.first_name, last_name=body.last_name,
            role=UserRole(body.role) if body.role else UserRole.seeker,
            is_verified=False, totp_secret=secret, onboarding_complete=False, is_assessment_done=True
        )
        if body.password:
            user.hashed_password = hash_password(body.password)
        db.add(user)
        await db.flush()
    else:
        if not user.totp_secret:
            user.totp_secret = totp_service.generate_secret()
        secret = user.totp_secret
        user.is_assessment_done = True

    # Check if AssessmentResult already exists
    res_query = await db.execute(select(AssessmentResult).where(AssessmentResult.session_id == session_id))
    assessment_result = res_query.scalar_one_or_none()
    if assessment_result:
        if assessment_result.user_id is None:
            assessment_result.user_id = user.id
        elif assessment_result.user_id != user.id:
            raise HTTPException(status_code=403, detail="Assessment already linked to another user")
        db.add(assessment_result)
    else:
        eval_data = await generate_assessment_evaluation(session.qa_history, session.experience_level, session.domain_interest)
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
    token = create_access_token(data={"sub": user.id})
    uri = totp_service.get_provisioning_uri(user.email or user.phone, secret)
    qr_base64 = totp_service.generate_qr_base64(uri)
    return LoginResponse(
        message="Assessment complete! Please scan the QR code to set up your account.",
        requires_setup=True, qr_code_base64=f"data:image/png;base64,{qr_base64}",
        user=UserOut.model_validate(user)
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
        eval_data = await generate_assessment_evaluation(session.qa_history, session.experience_level, session.domain_interest)
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
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
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
        eval_data = await generate_assessment_evaluation(session.qa_history, session.experience_level, session.domain_interest)
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
