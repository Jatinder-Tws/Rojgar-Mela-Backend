from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.career_enquiry_controller import (
    admin_list_career_enquiries as ctrl_list,
    admin_update_career_enquiry_status as ctrl_update_status,
    create_career_enquiry as ctrl_create,
)
from database import get_db
from models.user import User
from schemas.career_enquiry import (
    CareerEnquiryCreate,
    CareerEnquiryListResponse,
    CareerEnquiryOut,
    CareerEnquiryStatusUpdate,
    UnifiedEnquiryOut,
)
from services.auth_service import require_super_admin

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
    page_size: int = Query(20, ge=1, le=100),
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
