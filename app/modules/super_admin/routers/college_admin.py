from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin_or_permission
from app.modules.super_admin.controllers.college_controller import (
    create_college_ctrl, delete_college_ctrl, get_college_detail_ctrl,
    import_colleges_file_ctrl, list_colleges_ctrl, update_college_ctrl
)
from app.modules.super_admin.services.university_catalog_service import (
    build_admin_catalog,
    create_catalog_course,
    create_category,
    delete_catalog_course,
    delete_category,
    update_catalog_course,
    update_category,
    update_page_settings,
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


class CatalogSettingsIn(BaseModel):
    eyebrow_template: str
    lead_template: str
    rest_template: str


class CatalogCategoryIn(BaseModel):
    label: str
    hint: str = ""
    sort_order: int = 0
    is_active: bool = True


class CatalogCourseIn(BaseModel):
    category_id: str
    title: str
    subtitle: str | None = None
    badge_text: str | None = None
    badge_tone: str = "amber"
    badge_mode: str = "custom"
    icon_key: str = "graduation"
    match_course_name: str
    match_mode: str = "exact"
    sort_order: int = 0
    is_active: bool = True


@router.get("/catalog")
async def get_university_catalog(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_view", "colleges_manage", "colleges_courses", "colleges_accreditation")),
):
    return await build_admin_catalog(db)


@router.put("/catalog/settings")
async def save_university_page_settings(
    payload: CatalogSettingsIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage", "colleges_courses")),
):
    return await update_page_settings(db, payload.model_dump())


@router.post("/catalog/categories")
async def add_catalog_category(
    payload: CatalogCategoryIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage", "colleges_courses")),
):
    return await create_category(db, payload.model_dump())


@router.put("/catalog/categories/{category_id}")
async def edit_catalog_category(
    category_id: str,
    payload: CatalogCategoryIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage", "colleges_courses")),
):
    return await update_category(db, category_id, payload.model_dump())


@router.delete("/catalog/categories/{category_id}")
async def remove_catalog_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage")),
):
    return await delete_category(db, category_id)


@router.post("/catalog/courses")
async def add_catalog_course(
    payload: CatalogCourseIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage", "colleges_courses")),
):
    return await create_catalog_course(db, payload.model_dump())


@router.put("/catalog/courses/{course_id}")
async def edit_catalog_course(
    course_id: str,
    payload: CatalogCourseIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage", "colleges_courses")),
):
    return await update_catalog_course(db, course_id, payload.model_dump())


@router.delete("/catalog/courses/{course_id}")
async def remove_catalog_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin_or_permission("colleges_manage", "colleges_courses")),
):
    return await delete_catalog_course(db, course_id)


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
