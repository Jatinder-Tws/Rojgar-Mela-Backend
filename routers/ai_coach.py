from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from services.auth_service import require_seeker
from controllers.ai_coach_controller import (
    start_coach_session as ctrl_start_coach_session,
    respond_to_coach as ctrl_respond_to_coach,
    get_coach_result as ctrl_get_coach_result,
    get_my_coach_sessions as ctrl_get_my_coach_sessions,
)

router = APIRouter(prefix="/ai-coach", tags=["AI Coach"])


@router.post("/start")
async def start_coach_session(
    target_role: str = Body(...),
    experience_level: str = Body(...),
    focus_area: str = Body("General"),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_start_coach_session(target_role, experience_level, focus_area, user, db)


@router.post("/respond")
async def respond_to_coach(
    session_id: str = Body(...),
    answer: str = Body(...),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_respond_to_coach(session_id, answer, user, db)


@router.get("/result/{session_id}")
async def get_coach_result(session_id: str, user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_coach_result(session_id, user, db)


@router.get("/sessions/me")
async def get_my_coach_sessions(user: User = Depends(require_seeker), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_my_coach_sessions(user, db)
