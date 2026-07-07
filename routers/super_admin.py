"""
Super admin router – route definitions only.
Business logic lives in controllers/super_admin_controller.py
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.super_admin import (
    AdminApplicationListResponse, AdminAssessmentListResponse, AdminInterviewListResponse,
    AdminJobListResponse, AdminMatchListResponse, AdminProviderCreate, AdminProviderUpdate,
    AdminSeekerCreate, AdminSeekerUpdate, AdminSetPasswordRequest, AdminUserListResponse,
    AdminUserOut, BulkImportJobStarted, DashboardAnalyticsResponse, DetailedPlatformAnalytics,
    ImportJobStatus, PlatformStatsResponse, SuperAdminChangePasswordRequest, SuperAdminLoginRequest,
    SuperAdminLoginResponse, SuperAdminProfileOut, SuperAdminProfileUpdate,
)
from schemas.super_admin_detail import (
    AdminProviderDetailResponse, AdminSeekerDetailResponse,
)
from services.auth_service import require_super_admin
from controllers.super_admin_controller import (
    super_admin_login as ctrl_login,
    super_admin_me as ctrl_me,
    update_super_admin_profile as ctrl_update_profile,
    change_super_admin_password as ctrl_change_password,
    upload_super_admin_profile_pic as ctrl_upload_profile_pic,
    list_platform_jobs as ctrl_list_jobs,
    list_platform_matches as ctrl_list_matches,
    list_platform_applications as ctrl_list_applications,
    list_platform_interviews as ctrl_list_interviews,
    list_platform_assessments as ctrl_list_assessments,
    platform_stats as ctrl_platform_stats,
    detailed_platform_analytics as ctrl_detailed_analytics,
    dashboard_analytics as ctrl_dashboard_analytics,
    get_import_job_status as ctrl_import_job_status,
    list_seekers as ctrl_list_seekers,
    create_seeker as ctrl_create_seeker,
    get_seeker as ctrl_get_seeker,
    get_seeker_detail as ctrl_get_seeker_detail,
    update_seeker as ctrl_update_seeker,
    delete_seeker as ctrl_delete_seeker,
    set_seeker_password as ctrl_set_seeker_password,
    bulk_import_seekers as ctrl_bulk_import_seekers,
    list_providers as ctrl_list_providers,
    create_provider as ctrl_create_provider,
    get_provider as ctrl_get_provider,
    get_provider_detail as ctrl_get_provider_detail,
    update_provider as ctrl_update_provider,
    delete_provider as ctrl_delete_provider,
    set_provider_password as ctrl_set_provider_password,
    bulk_import_providers as ctrl_bulk_import_providers,
)

router = APIRouter(prefix="/super-admin", tags=["super-admin"])


@router.post("/login", response_model=SuperAdminLoginResponse)
async def super_admin_login(body: SuperAdminLoginRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_login(body, db)


@router.get("/me", response_model=SuperAdminProfileOut)
async def super_admin_me(admin: User = Depends(require_super_admin)):
    return ctrl_me(admin)


@router.put("/me", response_model=SuperAdminProfileOut)
async def update_super_admin_me(
    body: SuperAdminProfileUpdate,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_update_profile(admin, body, db)


@router.patch("/me/password", response_model=SuperAdminProfileOut)
async def change_super_admin_me_password(
    body: SuperAdminChangePasswordRequest,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_change_password(admin, body, db)


@router.post("/me/profile-pic", response_model=SuperAdminProfileOut)
async def upload_super_admin_profile_pic(
    file: UploadFile = File(...),
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_upload_profile_pic(file, admin, db)


@router.get("/jobs", response_model=AdminJobListResponse)
async def list_jobs(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    industry: Optional[str] = Query(None),
):
    return await ctrl_list_jobs(db, page, page_size, search, industry)


@router.get("/matches", response_model=AdminMatchListResponse)
async def list_matches(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
):
    return await ctrl_list_matches(db, page, page_size, search)


@router.get("/applications", response_model=AdminApplicationListResponse)
async def list_applications(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = Query(None),
):
    return await ctrl_list_applications(db, page, page_size, search, status)


@router.get("/interviews", response_model=AdminInterviewListResponse)
async def list_interviews(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
):
    return await ctrl_list_interviews(db, page, page_size, search)


@router.get("/assessments", response_model=AdminAssessmentListResponse)
async def list_assessments(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
):
    return await ctrl_list_assessments(db, page, page_size, search)


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_platform_stats(db)


@router.get("/analytics/detailed", response_model=DetailedPlatformAnalytics)
async def detailed_platform_analytics(admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_detailed_analytics(db)


@router.get("/analytics/dashboard", response_model=DashboardAnalyticsResponse)
async def dashboard_analytics(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    target_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD (legacy single day)"),
    start_date: Optional[str] = Query(None, description="Range start YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Range end YYYY-MM-DD"),
):
    parsed_target = datetime.fromisoformat(target_date) if target_date else None
    parsed_start = datetime.fromisoformat(start_date) if start_date else None
    parsed_end = datetime.fromisoformat(end_date) if end_date else None
    return await ctrl_dashboard_analytics(db, parsed_target, parsed_start, parsed_end)


@router.get("/import-jobs/{job_id}", response_model=ImportJobStatus)
async def get_import_job_status(job_id: str, admin: User = Depends(require_super_admin)):
    return ctrl_import_job_status(job_id)


# ── Job Seekers ──────────────────────────────────────────────────────────────

@router.get("/seekers", response_model=AdminUserListResponse)
async def list_seekers(
    admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None, industry: Optional[str] = Query(None),
    status: Optional[str] = Query(None), job_fair_id: Optional[str] = Query(None),
):
    return await ctrl_list_seekers(db, page, page_size, search, industry, status, job_fair_id)


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
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None, status: Optional[str] = Query(None),
):
    return await ctrl_list_providers(db, page, page_size, search, status)


@router.post("/providers", response_model=AdminUserOut, status_code=201)
async def create_provider(body: AdminProviderCreate, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_create_provider(body, db)


@router.get("/providers/{user_id}", response_model=AdminUserOut)
async def get_provider(user_id: str, admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_provider(user_id, db)


@router.get("/providers/{user_id}/detail", response_model=AdminProviderDetailResponse)
async def get_provider_detail(
    user_id: str,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_provider_detail(user_id, db)


@router.get("/seekers/{user_id}/detail", response_model=AdminSeekerDetailResponse)
async def get_seeker_detail(
    user_id: str,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_seeker_detail(user_id, db)


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
