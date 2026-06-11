from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.assessment import AssessmentStart, AssessmentAnswer, AssessmentComplete, AssessmentResultResponse
from services.auth_service import get_current_user
from controllers.assessment_controller import (
    start_assessment as ctrl_start_assessment,
    get_next_question as ctrl_get_next_question,
    submit_answer as ctrl_submit_answer,
    complete_assessment as ctrl_complete_assessment,
    get_result as ctrl_get_result,
    check_phone as ctrl_check_phone,
    get_by_user as ctrl_get_by_user,
    link_to_profile as ctrl_link_to_profile,
    get_my_assessment as ctrl_get_my_assessment,
)

router = APIRouter(prefix="/assessment", tags=["Assessment"])


@router.post("/start")
async def start_assessment(body: AssessmentStart, db: AsyncSession = Depends(get_db)):
    return await ctrl_start_assessment(body, db)


@router.get("/{session_id}/next")
async def get_next_question(session_id: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_get_next_question(session_id, db)


@router.post("/{session_id}/answer")
async def submit_answer(session_id: str, body: AssessmentAnswer, db: AsyncSession = Depends(get_db)):
    return await ctrl_submit_answer(session_id, body, db)


@router.post("/{session_id}/complete")
async def complete_assessment(session_id: str, body: AssessmentComplete, db: AsyncSession = Depends(get_db)):
    return await ctrl_complete_assessment(session_id, body, db)


@router.get("/{session_id}/result")
async def get_result(session_id: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_get_result(session_id, db)


@router.get("/check-phone/{phone}")
async def check_phone(phone: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_check_phone(phone, db)


@router.get("/user/{user_id}")
async def get_by_user(user_id: str, db: AsyncSession = Depends(get_db)):
    return await ctrl_get_by_user(user_id, db)


@router.post("/{session_id}/link")
async def link_to_profile(session_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ctrl_link_to_profile(session_id, user, db)


@router.get("/me")
async def get_my_assessment(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_my_assessment(user, db)
