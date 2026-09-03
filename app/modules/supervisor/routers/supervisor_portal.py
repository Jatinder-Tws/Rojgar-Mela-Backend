"""
Supervisor Portal Router.
Base prefix: /supervisor
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_supervisor
from app.modules.super_admin.schemas.supervisor import (
    SupervisorItemOut,
    SupervisorLoginRequest,
    SupervisorLoginResponse,
)
from app.modules.supervisor.controllers.supervisor_portal_controller import (
    supervisor_login,
    supervisor_me,
)
from app.shared.models.user import User

router = APIRouter(prefix="/supervisor", tags=["supervisor-portal"])


@router.post("/login", response_model=SupervisorLoginResponse)
async def api_supervisor_login(
    body: SupervisorLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await supervisor_login(body=body, db=db, request=request)


@router.get("/me", response_model=SupervisorItemOut)
async def api_supervisor_me(
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    return await supervisor_me(current_user=current_user, db=db)
