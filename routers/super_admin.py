"""
Super admin router – route definitions only.
Business logic lives in controllers/super_admin_controller.py
"""
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.super_admin import (
    AdminProviderCreate, AdminProviderUpdate, AdminSeekerCreate, AdminSeekerUpdate,
    AdminSetPasswordRequest, AdminUserListResponse, AdminUserOut, BulkImportJobStarted,
    DetailedPlatformAnalytics, ImportJobStatus, PlatformStatsResponse,
    SuperAdminLoginRequest, SuperAdminLoginResponse,
)
from services.auth_service import require_super_admin
from controllers.super_admin_controller import (
    super_admin_login as ctrl_login,
    super_admin_me as ctrl_me,
    platform_stats as ctrl_platform_stats,
    detailed_platform_analytics as ctrl_detailed_analytics,
    get_import_job_status as ctrl_import_job_status,
    list_seekers as ctrl_list_seekers,
    create_seeker as ctrl_create_seeker,
    get_seeker as ctrl_get_seeker,
    update_seeker as ctrl_update_seeker,
    delete_seeker as ctrl_delete_seeker,
    set_seeker_password as ctrl_set_seeker_password,
    bulk_import_seekers as ctrl_bulk_import_seekers,
    list_providers as ctrl_list_providers,
    create_provider as ctrl_create_provider,
    get_provider as ctrl_get_provider,
    update_provider as ctrl_update_provider,
    delete_provider as ctrl_delete_provider,
    set_provider_password as ctrl_set_provider_password,
    bulk_import_providers as ctrl_bulk_import_providers,
)

router = APIRouter(prefix="/super-admin", tags=["super-admin"])


@router.post("/login", response_model=SuperAdminLoginResponse)
async def super_admin_login(body: SuperAdminLoginRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_login(body, db)


@router.get("/me")
async def super_admin_me(admin: User = Depends(require_super_admin)):
    return ctrl_me(admin)


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_platform_stats(db)


@router.get("/analytics/detailed", response_model=DetailedPlatformAnalytics)
async def detailed_platform_analytics(admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_detailed_analytics(db)


@router.get("/import-jobs/{job_id}", response_model=ImportJobStatus)
async def get_import_job_status(job_id: str, admin: User = Depends(require_super_admin)):
    return ctrl_import_job_status(job_id)


# ── Job Seekers ──────────────────────────────────────────────────────────────

@router.get("/seekers", response_model=AdminUserListResponse)
async def list_seekers(
    admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None, welcome_email: Optional[str] = Query(None),
):
    return await ctrl_list_seekers(db, page, page_size, search, welcome_email)


@router.post("/seekers", response_model=AdminUserOut, status_code=201)
async def create_seeker(body: AdminSeekerCreate, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_create_seeker(body, db)


@router.get("/seekers/{user_id}", response_model=AdminUserOut)
async def get_seeker(user_id: str, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_seeker(user_id, db)


@router.put("/seekers/{user_id}", response_model=AdminUserOut)
async def update_seeker(user_id: str, body: AdminSeekerUpdate, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_seeker(user_id, body, db)


@router.delete("/seekers/{user_id}", status_code=204)
async def delete_seeker(user_id: str, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_delete_seeker(user_id, db)


@router.patch("/seekers/{user_id}/password", response_model=AdminUserOut)
async def set_seeker_password(user_id: str, body: AdminSetPasswordRequest, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_set_seeker_password(user_id, body, db)


@router.post("/seekers/bulk-import", response_model=BulkImportJobStarted)
async def bulk_import_seekers(admin: User = Depends(require_super_admin), file: UploadFile = File(...)):
    content = await file.read()
    return await ctrl_bulk_import_seekers(content, file.filename)


# ── Job Providers ────────────────────────────────────────────────────────────

@router.get("/providers", response_model=AdminUserListResponse)
async def list_providers(
    admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: Optional[str] = None,
):
    return await ctrl_list_providers(db, page, page_size, search)


@router.post("/providers", response_model=AdminUserOut, status_code=201)
async def create_provider(body: AdminProviderCreate, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_create_provider(body, db)


@router.get("/providers/{user_id}", response_model=AdminUserOut)
async def get_provider(user_id: str, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_provider(user_id, db)


@router.put("/providers/{user_id}", response_model=AdminUserOut)
async def update_provider(user_id: str, body: AdminProviderUpdate, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_provider(user_id, body, db)


@router.delete("/providers/{user_id}", status_code=204)
async def delete_provider(user_id: str, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_delete_provider(user_id, db)


@router.patch("/providers/{user_id}/password", response_model=AdminUserOut)
async def set_provider_password(user_id: str, body: AdminSetPasswordRequest, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_set_provider_password(user_id, body, db)


@router.post("/providers/bulk-import", response_model=BulkImportJobStarted)
async def bulk_import_providers(admin: User = Depends(require_super_admin), file: UploadFile = File(...)):
    content = await file.read()
    return await ctrl_bulk_import_providers(content, file.filename)
