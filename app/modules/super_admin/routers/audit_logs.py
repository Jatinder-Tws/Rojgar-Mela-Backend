"""
Super Admin Audit Logs router – access strictly restricted to Super-Admin.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin
from app.shared.models.user import User
from app.modules.super_admin.schemas.audit_logs import (
    AuditLogItem,
    AuditLogListResponse,
    AuditLogStatsResponse,
)
from app.modules.super_admin.controllers.audit_logs_controller import (
    list_audit_logs,
    get_audit_log_detail,
    get_audit_log_stats,
    export_audit_logs_csv,
)

router = APIRouter(prefix="/super-admin/audit-logs", tags=["super-admin-audit-logs"])


@router.get("", response_model=AuditLogListResponse)
async def api_list_audit_logs(
    role: Optional[str] = Query(None, description="Filter by actor role (supervisor, teacher, seeker, provider, student)"),
    action: Optional[str] = Query(None, description="Filter by action type (CREATE, UPDATE, DELETE, ATTENDANCE_MARK, etc.)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (batch, job, application, etc.)"),
    search: Optional[str] = Query(None, description="Search in name, email, description"),
    start_date: Optional[datetime] = Query(None, description="Start ISO datetime"),
    end_date: Optional[datetime] = Query(None, description="End ISO datetime"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Paginated activity and audit logs view for Super-Admin.
    Actions performed by Super-Admin are never recorded.
    """
    return await list_audit_logs(
        db=db,
        role=role,
        action=action,
        entity_type=entity_type,
        search=search,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=AuditLogStatsResponse)
async def api_get_audit_log_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Aggregated metrics and activity counts by user role and action.
    """
    return await get_audit_log_stats(db=db)


@router.get("/export")
async def api_export_audit_logs(
    role: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Exports filtered audit logs to a CSV stream.
    """
    return await export_audit_logs_csv(
        db=db,
        role=role,
        action=action,
        entity_type=entity_type,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{log_id}", response_model=AuditLogItem)
async def api_get_audit_log_detail(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Inspects full diff and request metadata for a specific audit log record.
    """
    return await get_audit_log_detail(db=db, log_id=log_id)
