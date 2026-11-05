"""
Super admin router – route definitions only.
Business logic lives in controllers/super_admin_controller.py
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.shared.models.user import User
from app.modules.super_admin.schemas.super_admin import (
    AdminApplicationListItem, AdminApplicationListResponse, AdminAssessmentListResponse, AdminInterviewListResponse,
    AdminJobCreate, AdminJobDetailResponse, AdminJobListResponse, AdminJobProviderOptionsResponse,
    AdminMatchListResponse, AdminProviderCreate, AdminProviderUpdate, AdminShortlistRequest,
    AdminSeekerCreate, AdminSeekerUpdate, AdminSetPasswordRequest, AdminUserExportRequest, AdminUserListResponse,
    AdminUserOut, BulkImportJobStarted, DashboardAnalyticsResponse, DetailedPlatformAnalytics,
    ImportJobStatus, PlatformStatsResponse, SuperAdminChangePasswordRequest, SuperAdminLoginRequest,
    SuperAdminLoginResponse, SuperAdminProfileOut, SuperAdminProfileUpdate,
)
from app.modules.super_admin.schemas.super_admin_detail import (
    AdminProviderDetailResponse, AdminSeekerDetailResponse,
)
from app.core.dependencies import require_super_admin, require_super_admin_or_permission, require_super_admin_or_supervisor
from app.modules.super_admin.controllers.super_admin_controller import (
    super_admin_login as ctrl_login,
    super_admin_me as ctrl_me,
    update_super_admin_profile as ctrl_update_profile,
    change_super_admin_password as ctrl_change_password,
    upload_super_admin_profile_pic as ctrl_upload_profile_pic,
    list_platform_jobs as ctrl_list_jobs,
    get_platform_job as ctrl_get_job,
    list_job_provider_options as ctrl_list_job_provider_options,
    create_platform_job as ctrl_create_platform_job,
    list_platform_matches as ctrl_list_matches,
    list_platform_applications as ctrl_list_applications,
    update_platform_application_status as ctrl_update_application_status,
    shortlist_platform_candidate as ctrl_shortlist_platform_candidate,
    list_platform_interviews as ctrl_list_interviews,
    list_platform_assessments as ctrl_list_assessments,
    platform_stats as ctrl_platform_stats,
    detailed_platform_analytics as ctrl_detailed_analytics,
    dashboard_analytics as ctrl_dashboard_analytics,
    get_import_job_status as ctrl_import_job_status,
    list_seekers as ctrl_list_seekers,
    list_seeker_industries as ctrl_list_seeker_industries,
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
    upload_provider_profile_pic as ctrl_upload_provider_profile_pic,
    get_provider_company_profile as ctrl_get_provider_company,
    admin_lookup_company as ctrl_admin_lookup_company,
    admin_apply_company_lookup as ctrl_admin_apply_company_lookup,
    upload_provider_gallery_image as ctrl_upload_provider_gallery,
    delete_provider_gallery_image as ctrl_delete_provider_gallery,
    bulk_import_providers as ctrl_bulk_import_providers,
    export_seekers as ctrl_export_seekers,
    export_providers as ctrl_export_providers,
)
from app.modules.jobs_portal.schemas.company_profile import (
    CompanyApplyLookupRequest,
    CompanyLookupRequest,
    CompanyLookupResponse,
    CompanyProfileOut,
)

router = APIRouter(prefix="/super-admin", tags=["super-admin"])


@router.post("/login", response_model=SuperAdminLoginResponse)
async def super_admin_login(body: SuperAdminLoginRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_login(body, db)


@router.get("/me", response_model=SuperAdminProfileOut)
async def super_admin_me(admin: User = Depends(require_super_admin_or_supervisor)):
    return ctrl_me(admin)


@router.put("/me", response_model=SuperAdminProfileOut)
async def update_super_admin_me(
    body: SuperAdminProfileUpdate,
    admin: User = Depends(require_super_admin_or_supervisor),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_update_profile(admin, body, db)


@router.patch("/me/password", response_model=SuperAdminProfileOut)
async def change_super_admin_me_password(
    body: SuperAdminChangePasswordRequest,
    admin: User = Depends(require_super_admin_or_supervisor),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_change_password(admin, body, db)


@router.post("/me/profile-pic", response_model=SuperAdminProfileOut)
async def upload_super_admin_profile_pic(
    file: UploadFile = File(...),
    admin: User = Depends(require_super_admin_or_supervisor),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_upload_profile_pic(file, admin, db)


@router.get("/jobs", response_model=AdminJobListResponse)
async def list_jobs(
    admin: User = Depends(require_super_admin_or_permission("jobs")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    industry: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    provider_id: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None, description="Posted from YYYY-MM-DD"),
    created_to: Optional[str] = Query(None, description="Posted to YYYY-MM-DD"),
):
    return await ctrl_list_jobs(
        db, page, page_size, search, industry, is_active, provider_id, created_from, created_to
    )


@router.get("/jobs/provider-options", response_model=AdminJobProviderOptionsResponse)
async def list_job_provider_options(
    admin: User = Depends(require_super_admin_or_permission("jobs")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    search: Optional[str] = None,
):
    return await ctrl_list_job_provider_options(db, page, page_size, search)


@router.post("/jobs", response_model=AdminJobDetailResponse, status_code=201)
async def create_job(
    body: AdminJobCreate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_super_admin_or_permission("jobs")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_create_platform_job(db, body, admin, background_tasks)


@router.get("/jobs/{job_id}", response_model=AdminJobDetailResponse)
async def get_job(
    job_id: str,
    admin: User = Depends(require_super_admin_or_permission("jobs")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_job(db, job_id)


@router.get("/matches", response_model=AdminMatchListResponse)
async def list_matches(
    admin: User = Depends(require_super_admin_or_permission("ai_matching")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    job_id: Optional[str] = Query(None),
    provider_id: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None, description="Match created from YYYY-MM-DD"),
    created_to: Optional[str] = Query(None, description="Match created to YYYY-MM-DD"),
):
    return await ctrl_list_matches(
        db, page, page_size, search, job_id, provider_id, created_from, created_to
    )


@router.get("/applications", response_model=AdminApplicationListResponse)
async def list_applications(
    admin: User = Depends(require_super_admin_or_permission("applications")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    provider_id: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None, description="Applied from YYYY-MM-DD"),
    created_to: Optional[str] = Query(None, description="Applied to YYYY-MM-DD"),
):
    return await ctrl_list_applications(
        db, page, page_size, search, status, job_id, provider_id, created_from, created_to
    )


@router.post("/applications/shortlist", response_model=AdminApplicationListItem, status_code=201)
async def shortlist_candidate(
    body: AdminShortlistRequest,
    admin: User = Depends(require_super_admin_or_permission("applications")),
    db: AsyncSession = Depends(get_db),
):
    """Shortlist a matched seeker for a job on behalf of that job's provider."""
    return await ctrl_shortlist_platform_candidate(db, body.seeker_id, body.job_id, admin)


@router.patch("/applications/{app_id}/status", response_model=AdminApplicationListItem)
async def update_application_status(
    app_id: str,
    body: dict,
    admin: User = Depends(require_super_admin_or_permission("applications")),
    db: AsyncSession = Depends(get_db),
):
    status = body.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="status is required")
    return await ctrl_update_application_status(
        db,
        app_id,
        str(status),
        admin,
        rejection_reason=body.get("rejection_reason"),
    )


@router.get("/interviews", response_model=AdminInterviewListResponse)
async def list_interviews(
    admin: User = Depends(require_super_admin_or_permission("applications")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    created_from: Optional[str] = Query(None, description="Scheduled from YYYY-MM-DD"),
    created_to: Optional[str] = Query(None, description="Scheduled to YYYY-MM-DD"),
):
    return await ctrl_list_interviews(db, page, page_size, search, created_from, created_to)


@router.get("/assessments", response_model=AdminAssessmentListResponse)
async def list_assessments(
    admin: User = Depends(require_super_admin_or_permission("applications")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
):
    return await ctrl_list_assessments(db, page, page_size, search)


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(admin: User = Depends(require_super_admin_or_supervisor), db: AsyncSession = Depends(get_db)):
    return await ctrl_platform_stats(db)


@router.get("/analytics/detailed", response_model=DetailedPlatformAnalytics)
async def detailed_platform_analytics(admin: User = Depends(require_super_admin_or_supervisor), db: AsyncSession = Depends(get_db)):
    return await ctrl_detailed_analytics(db)


@router.get("/analytics/dashboard", response_model=DashboardAnalyticsResponse)
async def dashboard_analytics(
    admin: User = Depends(require_super_admin_or_supervisor),
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
async def get_import_job_status(job_id: str, admin: User = Depends(require_super_admin_or_supervisor)):
    return ctrl_import_job_status(job_id)

# ── Job Seekers ──────────────────────────────────────────────────────────────
 
@router.get("/seekers", response_model=AdminUserListResponse)
async def list_seekers(
    admin: User = Depends(require_super_admin_or_permission("job_seekers")), db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None, industry: Optional[str] = Query(None),
    status: Optional[str] = Query(None), job_fair_id: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None), sort_dir: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None, description="Registered from YYYY-MM-DD"),
    created_to: Optional[str] = Query(None, description="Registered to YYYY-MM-DD"),
):
    return await ctrl_list_seekers(
        db, page, page_size, search, industry, status, job_fair_id, sort_by, sort_dir,
        created_from, created_to,
    )


@router.get("/seekers/industries", response_model=List[str])
async def list_seeker_industries(
    admin: User = Depends(require_super_admin_or_permission("job_seekers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_list_seeker_industries(db)


@router.post("/seekers", response_model=AdminUserOut, status_code=201)
async def create_seeker(body: AdminSeekerCreate, admin: User = Depends(require_super_admin_or_permission("job_seekers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_create_seeker(body, db)


@router.post("/seekers/export")
async def export_seekers(
    body: AdminUserExportRequest,
    admin: User = Depends(require_super_admin_or_permission("job_seekers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_export_seekers(body, db)


@router.post("/seekers/bulk-import", response_model=BulkImportJobStarted)
async def bulk_import_seekers(admin: User = Depends(require_super_admin_or_permission("job_seekers")), file: UploadFile = File(...)):
    content = await file.read()
    return await ctrl_bulk_import_seekers(content, file.filename)


@router.get("/seekers/{user_id}", response_model=AdminUserOut)
async def get_seeker(user_id: str, admin: User = Depends(require_super_admin_or_permission("job_seekers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_seeker(user_id, db)


@router.put("/seekers/{user_id}", response_model=AdminUserOut)
async def update_seeker(user_id: str, body: AdminSeekerUpdate, admin: User = Depends(require_super_admin_or_permission("job_seekers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_seeker(user_id, body, db)


@router.delete("/seekers/{user_id}", status_code=204)
async def delete_seeker(user_id: str, admin: User = Depends(require_super_admin_or_permission("job_seekers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_delete_seeker(user_id, db)


@router.patch("/seekers/{user_id}/password", response_model=AdminUserOut)
async def set_seeker_password(user_id: str, body: AdminSetPasswordRequest, admin: User = Depends(require_super_admin_or_permission("job_seekers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_set_seeker_password(user_id, body, db)


# ── Job Providers ────────────────────────────────────────────────────────────

@router.get("/providers", response_model=AdminUserListResponse)
async def list_providers(
    admin: User = Depends(require_super_admin_or_permission("job_providers")), db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None, status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None), sort_dir: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None, description="Registered from YYYY-MM-DD"),
    created_to: Optional[str] = Query(None, description="Registered to YYYY-MM-DD"),
    has_active_job: Optional[bool] = Query(None, description="Only providers with at least one active job"),
):
    return await ctrl_list_providers(
        db, page, page_size, search, status, sort_by, sort_dir, created_from, created_to, has_active_job
    )


@router.post("/providers", response_model=AdminUserOut, status_code=201)
async def create_provider(body: AdminProviderCreate, admin: User = Depends(require_super_admin_or_permission("job_providers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_create_provider(body, db)


@router.post("/providers/export")
async def export_providers(
    body: AdminUserExportRequest,
    admin: User = Depends(require_super_admin_or_permission("job_providers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_export_providers(body, db)


@router.post("/providers/bulk-import", response_model=BulkImportJobStarted)
async def bulk_import_providers(admin: User = Depends(require_super_admin_or_permission("job_providers")), file: UploadFile = File(...)):
    content = await file.read()
    return await ctrl_bulk_import_providers(content, file.filename)


@router.post("/providers/company-lookup", response_model=CompanyLookupResponse)
async def lookup_provider_company(
    body: CompanyLookupRequest,
    admin: User = Depends(require_super_admin_or_permission("job_providers")),
):
    return await ctrl_admin_lookup_company(body)


@router.get("/providers/{user_id}", response_model=AdminUserOut)
async def get_provider(user_id: str, admin: User = Depends(require_super_admin_or_permission("job_providers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_get_provider(user_id, db)


@router.get("/providers/{user_id}/detail", response_model=AdminProviderDetailResponse)
async def get_provider_detail(
    user_id: str,
    admin: User = Depends(require_super_admin_or_permission("job_providers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_provider_detail(user_id, db)


@router.get("/seekers/{user_id}/detail", response_model=AdminSeekerDetailResponse)
async def get_seeker_detail(
    user_id: str,
    admin: User = Depends(require_super_admin_or_permission("job_seekers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_seeker_detail(user_id, db)


@router.put("/providers/{user_id}", response_model=AdminUserOut)
async def update_provider(user_id: str, body: AdminProviderUpdate, admin: User = Depends(require_super_admin_or_permission("job_providers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_update_provider(user_id, body, db)


@router.delete("/providers/{user_id}", status_code=204)
async def delete_provider(user_id: str, admin: User = Depends(require_super_admin_or_permission("job_providers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_delete_provider(user_id, db)


@router.patch("/providers/{user_id}/password", response_model=AdminUserOut)
async def set_provider_password(user_id: str, body: AdminSetPasswordRequest, admin: User = Depends(require_super_admin_or_permission("job_providers")), db: AsyncSession = Depends(get_db)):
    return await ctrl_set_provider_password(user_id, body, db)


@router.post("/providers/{user_id}/profile-pic", response_model=AdminUserOut)
async def upload_provider_logo(
    user_id: str,
    file: UploadFile = File(...),
    admin: User = Depends(require_super_admin_or_permission("job_providers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_upload_provider_profile_pic(user_id, file, db)


@router.get("/providers/{user_id}/company", response_model=CompanyProfileOut)
async def get_provider_company(
    user_id: str,
    admin: User = Depends(require_super_admin_or_permission("job_providers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_provider_company(user_id, db)


@router.post("/providers/{user_id}/company/apply-lookup", response_model=CompanyProfileOut)
async def apply_provider_company_lookup(
    user_id: str,
    body: CompanyApplyLookupRequest,
    admin: User = Depends(require_super_admin_or_permission("job_providers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_admin_apply_company_lookup(user_id, body, db)


@router.post("/providers/{user_id}/company/gallery", response_model=CompanyProfileOut)
async def upload_provider_gallery(
    user_id: str,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    admin: User = Depends(require_super_admin_or_permission("job_providers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_upload_provider_gallery(user_id, file, db, caption)


@router.delete("/providers/{user_id}/company/gallery/{image_id}", response_model=CompanyProfileOut)
async def delete_provider_gallery(
    user_id: str,
    image_id: str,
    admin: User = Depends(require_super_admin_or_permission("job_providers")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_delete_provider_gallery(user_id, image_id, db)


@router.get("/auth-settings")
async def list_auth_settings(admin: User = Depends(require_super_admin_or_permission("social_login")), db: AsyncSession = Depends(get_db)):
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
    admin: User = Depends(require_super_admin_or_permission("social_login")),
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
    admin: User = Depends(require_super_admin_or_permission("social_login")),
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
