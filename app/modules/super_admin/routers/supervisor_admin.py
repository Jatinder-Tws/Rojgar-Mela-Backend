"""
Super Admin Supervisor Management Router.
Base prefix: /super-admin/supervisors
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin
from app.modules.super_admin.controllers.supervisor_admin_controller import (
    create_supervisor,
    delete_supervisor,
    get_permissions_catalog,
    get_supervisor,
    list_supervisors,
    reset_supervisor_password,
    update_supervisor,
    update_supervisor_status,
)
from app.modules.super_admin.schemas.supervisor import (
    SupervisorCreateRequest,
    SupervisorItemOut,
    SupervisorListResponse,
    SupervisorResetPasswordRequest,
    SupervisorStatusUpdateRequest,
    SupervisorUpdateRequest,
)
from app.shared.models.user import User

router = APIRouter(prefix="/super-admin/supervisors", tags=["super-admin-supervisors"])


@router.get("", response_model=SupervisorListResponse)
async def api_list_supervisors(
    search: Optional[str] = Query(None, description="Search by name, email, or department"),
    department: Optional[str] = Query(None, description="Filter by department"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_supervisors(
        db=db,
        search=search,
        department=department,
        is_active=is_active,
        page=page,
        limit=limit,
    )


@router.get("/permissions-catalog")
async def api_get_permissions_catalog(
    _admin: User = Depends(require_super_admin),
):
    return await get_permissions_catalog()


@router.get("/{supervisor_id}", response_model=SupervisorItemOut)
async def api_get_supervisor(
    supervisor_id: str,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_supervisor(supervisor_id=supervisor_id, db=db)


@router.post("", response_model=SupervisorItemOut)
async def api_create_supervisor(
    body: SupervisorCreateRequest,
    current_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await create_supervisor(body=body, current_admin=current_admin, db=db)


@router.put("/{supervisor_id}", response_model=SupervisorItemOut)
async def api_update_supervisor(
    supervisor_id: str,
    body: SupervisorUpdateRequest,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await update_supervisor(supervisor_id=supervisor_id, body=body, db=db)


@router.patch("/{supervisor_id}/status", response_model=SupervisorItemOut)
async def api_update_supervisor_status(
    supervisor_id: str,
    body: SupervisorStatusUpdateRequest,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await update_supervisor_status(supervisor_id=supervisor_id, body=body, db=db)


@router.post("/{supervisor_id}/reset-password")
async def api_reset_supervisor_password(
    supervisor_id: str,
    body: SupervisorResetPasswordRequest,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await reset_supervisor_password(supervisor_id=supervisor_id, body=body, db=db)


@router.delete("/{supervisor_id}")
async def api_delete_supervisor(
    supervisor_id: str,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await delete_supervisor(supervisor_id=supervisor_id, db=db)
