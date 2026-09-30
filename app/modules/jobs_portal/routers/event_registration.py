from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin_or_permission
from app.modules.jobs_portal.controllers import event_registration_controller as ctrl
from app.modules.jobs_portal.schemas.event_registration import (
    EventFormCreate,
    EventFormListResponse,
    EventFormOut,
    EventFormPublicOut,
    EventFormUpdate,
    EventPrizeIn,
    EventPrizeOut,
    EventPrizeUpdate,
    EventRegisterIn,
    EventRegisterPendingOut,
    EventResendOtpIn,
    EventSubmissionListResponse,
    EventTestDrawOut,
    EventTicketOut,
    EventVerifyOtpIn,
)
from app.shared.models.user import User

public_router = APIRouter(prefix="/event-registrations", tags=["event-registrations"])
admin_router = APIRouter(prefix="/super-admin/event-registrations", tags=["super-admin-event-registrations"])


@public_router.get("/{slug}", response_model=EventFormPublicOut)
async def get_public_form(slug: str, db: AsyncSession = Depends(get_db)):
    return await ctrl.get_public_form(slug, db)


@public_router.post("/{slug}/register", response_model=EventRegisterPendingOut, status_code=201)
async def register(slug: str, body: EventRegisterIn, db: AsyncSession = Depends(get_db)):
    return await ctrl.register_pending(slug, body.answers, db)


@public_router.post("/{slug}/verify-otp", response_model=EventTicketOut)
async def verify_otp(slug: str, body: EventVerifyOtpIn, db: AsyncSession = Depends(get_db)):
    return await ctrl.verify_otp(slug, body, db)


@public_router.post("/{slug}/resend-otp", response_model=EventRegisterPendingOut)
async def resend_otp(slug: str, body: EventResendOtpIn, db: AsyncSession = Depends(get_db)):
    return await ctrl.resend_otp(slug, body.pending_id, db)


@admin_router.get("", response_model=EventFormListResponse)
async def list_forms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await ctrl.list_forms(db, page=page, page_size=page_size, search=search)
    return EventFormListResponse(items=items, total=total, page=page, page_size=page_size)


@admin_router.post("", response_model=EventFormOut, status_code=201)
async def create_form(
    body: EventFormCreate,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.create_form(body, db)


@admin_router.get("/{form_id}", response_model=EventFormOut)
async def get_form(
    form_id: str,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.get_form(form_id, db)


@admin_router.patch("/{form_id}", response_model=EventFormOut)
async def update_form(
    form_id: str,
    body: EventFormUpdate,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.update_form(form_id, body, db)


@admin_router.delete("/{form_id}", status_code=204)
async def delete_form(
    form_id: str,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    await ctrl.delete_form(form_id, db)


@admin_router.get("/{form_id}/submissions", response_model=EventSubmissionListResponse)
async def list_submissions(
    form_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.list_submissions(form_id, db, page=page, page_size=page_size, search=search)


@admin_router.post("/{form_id}/prizes", response_model=EventPrizeOut, status_code=201)
async def create_prize(
    form_id: str,
    body: EventPrizeIn,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.create_prize(form_id, body, db)


@admin_router.patch("/{form_id}/prizes/{prize_id}", response_model=EventPrizeOut)
async def update_prize(
    form_id: str,
    prize_id: str,
    body: EventPrizeUpdate,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl.update_prize(form_id, prize_id, body, db)


@admin_router.delete("/{form_id}/prizes/{prize_id}", status_code=204)
async def delete_prize(
    form_id: str,
    prize_id: str,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    await ctrl.delete_prize(form_id, prize_id, db)


@admin_router.post("/{form_id}/test-draw", response_model=EventTestDrawOut)
async def test_draw(
    form_id: str,
    _admin: User = Depends(require_super_admin_or_permission("event_registrations")),
    db: AsyncSession = Depends(get_db),
):
    data = await ctrl.test_draw(form_id, db)
    return EventTestDrawOut(**data)
