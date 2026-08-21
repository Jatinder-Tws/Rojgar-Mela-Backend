"""
Super admin router – route definitions only.
Business logic lives in controllers/super_admin_controller.py
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.modules.super_admin.schemas.super_admin import (
    AdminApplicationListItem, AdminApplicationListResponse, AdminAssessmentListResponse, AdminInterviewListResponse,
    AdminJobListResponse, AdminMatchListResponse, AdminProviderCreate, AdminProviderUpdate,
    AdminSeekerCreate, AdminSeekerUpdate, AdminSetPasswordRequest, AdminUserExportRequest, AdminUserListResponse,
    AdminUserOut, BulkImportJobStarted, DashboardAnalyticsResponse, DetailedPlatformAnalytics,
    ImportJobStatus, PlatformStatsResponse, SuperAdminChangePasswordRequest, SuperAdminLoginRequest,
    SuperAdminLoginResponse, SuperAdminProfileOut, SuperAdminProfileUpdate,
)
from app.modules.super_admin.schemas.super_admin_detail import (
    AdminProviderDetailResponse, AdminSeekerDetailResponse,
)
from app.core.dependencies import require_super_admin
from app.modules.super_admin.controllers.super_admin_controller import (
    super_admin_login as ctrl_login,
    super_admin_me as ctrl_me,
    update_super_admin_profile as ctrl_update_profile,
    change_super_admin_password as ctrl_change_password,
    upload_super_admin_profile_pic as ctrl_upload_profile_pic,
    list_platform_jobs as ctrl_list_jobs,
    list_platform_matches as ctrl_list_matches,
    list_platform_applications as ctrl_list_applications,
    update_platform_application_status as ctrl_update_application_status,
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
    export_seekers as ctrl_export_seekers,
    export_providers as ctrl_export_providers,
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
    is_active: Optional[bool] = Query(None),
):
    return await ctrl_list_jobs(db, page, page_size, search, industry, is_active)


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


@router.patch("/applications/{app_id}/status", response_model=AdminApplicationListItem)
async def update_application_status(
    app_id: str,
    body: dict,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    status = body.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="status is required")
    return await ctrl_update_application_status(
        db,
        app_id,
        str(status),
        rejection_reason=body.get("rejection_reason"),
    )


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


@router.post("/seekers/export")
async def export_seekers(
    body: AdminUserExportRequest,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_export_seekers(body, db)


@router.post("/seekers/bulk-import", response_model=BulkImportJobStarted)
async def bulk_import_seekers(admin: User = Depends(require_super_admin), file: UploadFile = File(...)):
    content = await file.read()
    return await ctrl_bulk_import_seekers(content, file.filename)


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


@router.post("/providers/export")
async def export_providers(
    body: AdminUserExportRequest,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_export_providers(body, db)


@router.post("/providers/bulk-import", response_model=BulkImportJobStarted)
async def bulk_import_providers(admin: User = Depends(require_super_admin), file: UploadFile = File(...)):
    content = await file.read()
    return await ctrl_bulk_import_providers(content, file.filename)


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


@router.get("/auth-settings")
async def list_auth_settings(admin: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    from app.shared.services import auth_provider_settings_service as provider_settings
    from app.shared.services.oauth_providers import provider_configured

    rows = await provider_settings.get_all_settings(db)
    return [
        {
            "provider": row.provider,
            "is_enabled": row.is_enabled,
            "enabled_for_roles": list(row.enabled_for_roles or []),
            "enabled_on_register": row.enabled_on_register,
            "enabled_on_login": row.enabled_on_login,
            "display_order": int(row.display_order or 99),
            "configured": provider_configured(row.provider),
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.put("/auth-settings/{provider}")
async def update_auth_settings(
    provider: str,
    body: dict,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.shared.schemas.social_auth import AdminAuthProviderUpdate
    from app.shared.services import auth_provider_settings_service as provider_settings
    from app.shared.services.oauth_providers import PROVIDERS, provider_configured

    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown provider")
    parsed = AdminAuthProviderUpdate.model_validate(body)
    row = await provider_settings.update_provider_settings(
        db,
        provider,
        is_enabled=parsed.is_enabled,
        enabled_for_roles=parsed.enabled_for_roles,
        enabled_on_register=parsed.enabled_on_register,
        enabled_on_login=parsed.enabled_on_login,
        display_order=parsed.display_order,
        admin_id=admin.id,
    )
    return {
        "provider": row.provider,
        "is_enabled": row.is_enabled,
        "enabled_for_roles": list(row.enabled_for_roles or []),
        "enabled_on_register": row.enabled_on_register,
        "enabled_on_login": row.enabled_on_login,
        "display_order": int(row.display_order or 99),
        "configured": provider_configured(row.provider),
        "updated_at": row.updated_at,
    }


@router.get("/auth-settings/history")
async def auth_settings_history(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.shared.models.auth_provider_settings import AuthSettingsHistory

    rows = (
        await db.execute(select(AuthSettingsHistory).order_by(AuthSettingsHistory.changed_at.desc()).limit(50))
    ).scalars().all()
    return [
        {
            "id": row.id,
            "provider": row.provider,
            "changed_by": row.changed_by,
            "old_value": row.old_value,
            "new_value": row.new_value,
            "changed_at": row.changed_at,
        }
        for row in rows
    ]
