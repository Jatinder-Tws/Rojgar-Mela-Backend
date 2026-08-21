from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.core.dependencies import require_seeker
from app.modules.jobs_portal.controllers.ai_coach_controller import (
    start_coach_session as ctrl_start_coach_session,
    start_live_coach_session as ctrl_start_live_coach_session,
    respond_to_coach as ctrl_respond_to_coach,
    get_coach_result as ctrl_get_coach_result,
    get_my_coach_sessions as ctrl_get_my_coach_sessions,
    get_credit_balance as ctrl_get_credit_balance,
    process_heartbeat as ctrl_process_heartbeat,
    create_credit_order as ctrl_create_credit_order,
    verify_credit_order as ctrl_verify_credit_order,
    get_active_room_session as ctrl_get_active_room_session,
)

router = APIRouter(prefix="/ai-coach", tags=["AI Coach"])


@router.get("/credits/balance")
async def get_credit_balance(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_credit_balance(user, db)


@router.post("/credits/order")
async def create_credit_order(
    package_id: str = Body(..., embed=True),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_create_credit_order(package_id, user, db)


@router.post("/credits/verify")
async def verify_credit_order(
    provider_order_id: str = Body(...),
    provider_payment_id: str = Body(...),
    provider_signature: str = Body(...),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_verify_credit_order(
        provider_order_id, provider_payment_id, provider_signature, user, db
    )


@router.post("/session/heartbeat")
async def process_heartbeat(
    session_id: str = Body(..., embed=True),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_process_heartbeat(session_id, user, db)


@router.post("/start")
async def start_coach_session(
    target_role: str = Body(...),
    experience_level: str = Body(...),
    focus_area: str = Body("General"),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_start_coach_session(target_role, experience_level, focus_area, user, db)


@router.post("/start-live")
async def start_live_coach_session(
    target_role: str = Body(...),
    experience_level: str = Body(...),
    focus_area: str = Body("General"),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_start_live_coach_session(target_role, experience_level, focus_area, user, db)


@router.post("/respond")
async def respond_to_coach(
    session_id: str = Body(...),
    answer: str = Body(...),
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_respond_to_coach(session_id, answer, user, db)


@router.get("/result/{session_id}")
async def get_coach_result(
    session_id: str,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_coach_result(session_id, user, db)


@router.get("/sessions/me")
async def get_my_coach_sessions(
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_my_coach_sessions(user, db)


@router.get("/room/{session_id}")
async def get_active_room_session(
    session_id: str,
    user: User = Depends(require_seeker),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_active_room_session(session_id, user, db)

