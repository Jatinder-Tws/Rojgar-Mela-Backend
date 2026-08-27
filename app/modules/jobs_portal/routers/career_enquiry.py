from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.controllers.career_enquiry_controller import (
    admin_delete_enquiry as ctrl_delete,
    admin_list_career_enquiries as ctrl_list,
    admin_update_career_enquiry_status as ctrl_update_status,
    create_career_enquiry as ctrl_create,
)
from app.core.database import get_db
from app.shared.models.user import User
from app.modules.jobs_portal.schemas.career_enquiry import (
    CareerEnquiryCreate,
    CareerEnquiryListResponse,
    CareerEnquiryOut,
    CareerEnquiryStatusUpdate,
    UnifiedEnquiryOut,
)
from app.core.dependencies import require_super_admin

# Public submit + super-admin management under one router module
public_router = APIRouter(prefix="/career-program", tags=["career-program"])
admin_router = APIRouter(prefix="/super-admin/enquiries", tags=["super-admin-enquiries"])


@public_router.post("/enquiries", response_model=CareerEnquiryOut, status_code=201)
async def create_enquiry(
    body: CareerEnquiryCreate,
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_create(body, db)


@admin_router.get("", response_model=CareerEnquiryListResponse)
async def list_enquiries(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
    source: Optional[str] = None,
    _admin: User = Depends(require_super_admin),
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
    )


@admin_router.patch("/{enquiry_id}/status", response_model=UnifiedEnquiryOut)
async def update_enquiry_status(
    enquiry_id: str,
    body: CareerEnquiryStatusUpdate,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_update_status(enquiry_id, body, db)


@admin_router.delete("/{enquiry_id}", status_code=204)
async def delete_enquiry(
    enquiry_id: str,
    source: str = Query("career"),
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    await ctrl_delete(enquiry_id, source, db)
