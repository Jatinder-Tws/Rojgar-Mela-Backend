from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin_or_permission
from app.modules.super_admin.controllers.college_controller import (
    create_college_ctrl, delete_college_ctrl, get_college_detail_ctrl,
    import_colleges_file_ctrl, list_colleges_ctrl, update_college_ctrl
)
from app.modules.super_admin.schemas.college_schemas import (
    CollegeCreate, CollegeDetailOut, CollegeListResponse, CollegeUpdate,
    ExcelImportSummary
)
from app.shared.models.user import User

router = APIRouter(prefix="/api/v1/super-admin/colleges", tags=["Super Admin - Colleges & Universities"])


@router.get("", response_model=CollegeListResponse)
async def list_colleges(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_view", "colleges_manage", "colleges_courses", "colleges_accreditation")),
):
    """List colleges with filtering, search and pagination."""
    return await list_colleges_ctrl(
        db=db,
        page=page,
        limit=limit,
        search=search,
        state=state,
        city=city,
        ctype=type,
        is_active=is_active,
    )


@router.get("/{id_or_slug}", response_model=CollegeDetailOut)
async def get_college_detail(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_view", "colleges_manage", "colleges_courses", "colleges_accreditation")),
):
    """Retrieve full details of a college/university."""
    return await get_college_detail_ctrl(db, id_or_slug)


@router.post("", response_model=CollegeDetailOut)
async def create_college(
    payload: CollegeCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage")),
):
    """Create a new college/university record with sub-sections."""
    return await create_college_ctrl(db, payload)


@router.put("/{college_id}", response_model=CollegeDetailOut)
async def update_college(
    college_id: str,
    payload: CollegeUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage", "colleges_courses", "colleges_accreditation")),
):
    """Update college details, courses, approvals, or EMI plans."""
    return await update_college_ctrl(db, college_id, payload)


@router.delete("/{college_id}")
async def delete_college(
    college_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage")),
):
    """Delete a college and all cascade-related data."""
    return await delete_college_ctrl(db, college_id)


@router.post("/import-excel", response_model=ExcelImportSummary)
async def import_colleges_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage")),
):
    """Bulk import / update colleges from multi-sheet Excel or CSV file without duplicates."""
    return await import_colleges_file_ctrl(db, file)
