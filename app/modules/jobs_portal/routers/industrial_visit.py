from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin_or_permission
from app.modules.jobs_portal.controllers import industrial_visit_controller as ctrl
from app.modules.jobs_portal.schemas.industrial_visit import (
    IndustrialVisitAdminListResponse,
    IndustrialVisitAdminOut,
    IndustrialVisitAttendanceUpdate,
    IndustrialVisitCertificateVerifyOut,
    IndustrialVisitCheckIn,
    IndustrialVisitCheckInOut,
    IndustrialVisitCheckInPublicOut,
    IndustrialVisitCreate,
    IndustrialVisitPublicOut,
    IndustrialVisitRegister,
    IndustrialVisitRegisterOut,
    IndustrialVisitSendCertificatesOut,
    IndustrialVisitStudentListResponse,
    IndustrialVisitStudentOut,
    IndustrialVisitUpdate,
)
from app.shared.models.user import User

public_router = APIRouter(prefix="/industrial-visits", tags=["industrial-visits"])
admin_router = APIRouter(prefix="/super-admin/industrial-visits", tags=["super-admin-industrial-visits"])


@public_router.get("/default", response_model=IndustrialVisitPublicOut)
async def get_default_visit(db: AsyncSession = Depends(get_db)):
    return await ctrl.get_public_visit("default", db)


@public_router.get("/certificates/{certificate_id}", response_model=IndustrialVisitCertificateVerifyOut)
async def verify_certificate(certificate_id: str, db: AsyncSession = Depends(get_db)):
    return await ctrl.verify_certificate(certificate_id, db)


@public_router.get("/in/{check_in_slug}", response_model=IndustrialVisitCheckInPublicOut)
async def get_check_in_visit(check_in_slug: str, db: AsyncSession = Depends(get_db)):
    return await ctrl.get_check_in_visit(check_in_slug, db)


@public_router.post("/in/{check_in_slug}/check-in", response_model=IndustrialVisitCheckInOut)
async def check_in(
    check_in_slug: str,
    body: IndustrialVisitCheckIn,
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.check_in_student(check_in_slug, body, db)


@public_router.get("/{slug}", response_model=IndustrialVisitPublicOut)
async def get_public_visit(slug: str, db: AsyncSession = Depends(get_db)):
    return await ctrl.get_public_visit(slug, db)


@public_router.post("/{slug}/register", response_model=IndustrialVisitRegisterOut, status_code=201)
async def register_student(
    slug: str,
    body: IndustrialVisitRegister,
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.register_student(slug, body, db)


@admin_router.get("", response_model=IndustrialVisitAdminListResponse)
async def list_visits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.admin_list_visits(db, page=page, page_size=page_size, search=search)


@admin_router.post("", response_model=IndustrialVisitAdminOut, status_code=201)
async def create_visit(
    body: IndustrialVisitCreate,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.admin_create_visit(body, db)


@admin_router.get("/{visit_id}", response_model=IndustrialVisitAdminOut)
async def get_visit(
    visit_id: str,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.admin_get_visit(visit_id, db)


@admin_router.patch("/{visit_id}", response_model=IndustrialVisitAdminOut)
async def update_visit(
    visit_id: str,
    body: IndustrialVisitUpdate,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.admin_update_visit(visit_id, body, db)


@admin_router.delete("/{visit_id}", status_code=204)
async def delete_visit(
    visit_id: str,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    await ctrl.admin_delete_visit(visit_id, db)


@admin_router.get("/{visit_id}/students", response_model=IndustrialVisitStudentListResponse)
async def list_students(
    visit_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    college: Optional[str] = None,
    department: Optional[str] = None,
    attendance: Optional[str] = None,
    certificate: Optional[str] = None,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.admin_list_students(
        visit_id,
        db,
        page=page,
        page_size=page_size,
        search=search,
        college=college,
        department=department,
        attendance=attendance,
        certificate=certificate,
    )


@admin_router.get("/{visit_id}/students/export")
async def export_students(
    visit_id: str,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.admin_export_students_csv(visit_id, db)


@admin_router.patch("/{visit_id}/students/{student_id}/attendance", response_model=IndustrialVisitStudentOut)
async def update_attendance(
    visit_id: str,
    student_id: str,
    body: IndustrialVisitAttendanceUpdate,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.admin_update_attendance(visit_id, student_id, body, db)


@admin_router.post("/{visit_id}/send-certificates", response_model=IndustrialVisitSendCertificatesOut)
async def send_certificates(
    visit_id: str,
    _admin: User = Depends(require_super_admin_or_permission("industrial_visits")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.admin_send_certificates(visit_id, db)
