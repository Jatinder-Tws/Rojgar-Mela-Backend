"""
Gemini Live voice interview WebSocket route.

Handles auth (query-param JWT, since browsers can't set a custom Authorization
header on a WS handshake) and session-ownership checks, then hands off to
ai_coach_live_service.run_live_session for the actual Gemini Live connection
lifecycle.

DB access here is deliberately scoped to a short-lived session (`async with
AsyncSessionLocal()`) rather than a request-scoped `Depends(get_db)` session,
because a `Depends(get_db)` session would stay checked out from the connection
pool for the WS handler's entire lifetime - i.e. the whole live call, which can
run for minutes. With pool_size=10/max_overflow=20 (see app/core/database.py),
a handful of concurrent live calls holding a connection the whole time would
starve other requests of DB connections. run_live_session instead opens its own
short-lived session only when it actually needs one (finalize step).
"""
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.dependencies import get_current_user_ws
from app.modules.jobs_portal.models.ai_coach import AICoachSession
from app.modules.jobs_portal.services.ai_coach_credits_service import AICoachCreditsService
from app.modules.jobs_portal.services.ai_coach_live_service import run_live_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/ai-coach-live", tags=["AI Coach Live"])

WS_AUTH_FAILED = 4001
WS_SESSION_NOT_FOUND = 4004


@router.websocket("/{session_id}")
async def ai_coach_live_ws(websocket: WebSocket, session_id: str):
    async with AsyncSessionLocal() as db:
        user = await get_current_user_ws(websocket, db)
        if user is None:
            await websocket.close(code=WS_AUTH_FAILED)
            return

        try:
            AICoachCreditsService.verify_seeker_role(user)
        except HTTPException:
            await websocket.close(code=WS_AUTH_FAILED)
            return

        result = await db.execute(select(AICoachSession).where(AICoachSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session or session.seeker_id != user.id:
            await websocket.close(code=WS_SESSION_NOT_FOUND)
            return

        target_role = session.target_role
        experience_level = session.experience_level
        focus_area = session.focus_area
        seeker_id = session.seeker_id
    # `db` (and its pool connection) is released here, before the potentially
    # multi-minute live call begins.

    await websocket.accept()
    await websocket.send_json({"type": "session_started", "session_id": session_id})

    try:
        await run_live_session(
            websocket=websocket,
            session_id=session_id,
            seeker_id=seeker_id,
            target_role=target_role,
            experience_level=experience_level,
            focus_area=focus_area,
        )
    except WebSocketDisconnect:
        logger.info("AI Coach live WS disconnected (session_id=%s, user_id=%s)", session_id, user.id)
