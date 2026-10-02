from typing import Optional
from io import BytesIO

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.controllers.career_enquiry_controller import (
    admin_create_enquiry as ctrl_admin_create,
    admin_delete_enquiry as ctrl_delete,
    admin_export_enquiries_xlsx as ctrl_export,
    admin_get_enquiry as ctrl_get,
    admin_enquiry_pipeline_stats as ctrl_stats,
    admin_import_enquiries as ctrl_import,
    admin_list_career_enquiries as ctrl_list,
    admin_update_career_enquiry_status as ctrl_update_status,
    create_career_enquiry as ctrl_create,
    enquiry_import_template as ctrl_template,
)
from app.core.database import get_db
from app.shared.models.user import User
from app.modules.jobs_portal.schemas.career_enquiry import (
    AdminManualEnquiryCreate,
    CareerEnquiryCreate,
    CareerEnquiryListResponse,
    CareerEnquiryOut,
    CareerEnquiryStatusUpdate,
    EnquiryImportResult,
    EnquiryPipelineStats,
    UnifiedEnquiryOut,
)
from app.core.dependencies import require_super_admin_or_permission

# Public submit + super-admin management under one router module
public_router = APIRouter(prefix="/career-program", tags=["career-program"])
admin_router = APIRouter(prefix="/super-admin/enquiries", tags=["super-admin-enquiries"])


@public_router.post("/enquiries", response_model=CareerEnquiryOut, status_code=201)
async def create_enquiry(
    body: CareerEnquiryCreate,
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_create(body, db)


@admin_router.post("", response_model=UnifiedEnquiryOut, status_code=201)
async def create_manual_enquiry(
    body: AdminManualEnquiryCreate,
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_admin_create(body, db)


@admin_router.get("/import-template")
async def download_enquiry_import_template(
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
):
    return ctrl_template()


@admin_router.post("/import", response_model=EnquiryImportResult)
async def import_enquiries(
    file: UploadFile = File(...),
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_import(file, db)


@admin_router.get("/stats", response_model=EnquiryPipelineStats)
async def enquiry_pipeline_stats(
    source: Optional[str] = Query("all"),
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_stats(db, source=source)


@admin_router.get("/export")
async def export_enquiries(
    search: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    objection: Optional[str] = None,
    follow_up: Optional[str] = None,
    announcement_id: Optional[str] = None,
    draw_date: Optional[str] = None,
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
    db: AsyncSession = Depends(get_db),
):
    payload = await ctrl_export(
        db,
        search=search,
        status=status,
        source=source,
        objection=objection,
        follow_up=follow_up,
        announcement_id=announcement_id,
        draw_date=draw_date,
    )
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="enquiries.xlsx"'},
    )


@admin_router.get("/{enquiry_id}", response_model=UnifiedEnquiryOut)
async def get_enquiry(
    enquiry_id: str,
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get(enquiry_id, db)


@admin_router.get("", response_model=CareerEnquiryListResponse)
async def list_enquiries(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
    source: Optional[str] = None,
    objection: Optional[str] = None,
    follow_up: Optional[str] = None,
    announcement_id: Optional[str] = None,
    draw_date: Optional[str] = None,
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_list(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        domain=domain,
        qualification=qualification,
        source=source,
        objection=objection,
        follow_up=follow_up,
        announcement_id=announcement_id,
        draw_date=draw_date,
    )


@admin_router.patch("/{enquiry_id}/status", response_model=UnifiedEnquiryOut)
async def update_enquiry_status(
    enquiry_id: str,
    body: CareerEnquiryStatusUpdate,
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_update_status(enquiry_id, body, db)


@admin_router.delete("/{enquiry_id}", status_code=204)
async def delete_enquiry(
    enquiry_id: str,
    source: str = Query("career"),
    _admin: User = Depends(require_super_admin_or_permission("enquiries")),
    db: AsyncSession = Depends(get_db),
):
    await ctrl_delete(enquiry_id, source, db)

