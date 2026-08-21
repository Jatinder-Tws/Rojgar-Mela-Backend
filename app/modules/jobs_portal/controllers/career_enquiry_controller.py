import logging
import re
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.models.career_enquiry import DEFAULT_STATUS, CareerEnquiry
from app.modules.super_admin.models.contact_inquiry import DEFAULT_CONTACT_STATUS, ContactInquiry
from app.shared.models.notification import NotificationType
from app.modules.jobs_portal.schemas.career_enquiry import (
    VALID_ENQUIRY_STATUSES,
    CareerEnquiryCreate,
    CareerEnquiryListResponse,
    CareerEnquiryOut,
    CareerEnquiryStatusUpdate,
    UnifiedEnquiryOut,
)
from app.shared.services.notification_service import notify_super_admins

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits


def _career_to_out(item: CareerEnquiry) -> CareerEnquiryOut:
    return CareerEnquiryOut(
        id=item.id,
        full_name=item.full_name,
        email=item.email,
        phone=item.phone,
        qualification=item.qualification,
        domain=item.domain,
        message=item.message,
        status=item.status,
        admin_notes=item.admin_notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _career_to_unified(item: CareerEnquiry) -> UnifiedEnquiryOut:
    return UnifiedEnquiryOut(
        id=item.id,
        source="career",
        name=item.full_name,
        email=item.email,
        phone=item.phone,
        qualification=item.qualification,
        domain=item.domain,
        subject=None,
        message=item.message,
        status=item.status or DEFAULT_STATUS,
        admin_notes=item.admin_notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _contact_to_unified(item: ContactInquiry) -> UnifiedEnquiryOut:
    return UnifiedEnquiryOut(
        id=item.id,
        source="contact",
        name=item.name,
        email=item.email,
        phone=item.phone,
        qualification=None,
        domain=None,
        subject=item.subject,
        message=item.message,
        status=item.status or DEFAULT_CONTACT_STATUS,
        admin_notes=item.admin_notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def create_career_enquiry(body: CareerEnquiryCreate, db: AsyncSession) -> CareerEnquiryOut:
    phone = _normalize_phone(body.phone)
    if len(phone) < 10 or len(phone) > 12:
        raise HTTPException(status_code=400, detail="Enter a valid 10–12 digit phone number")

    message = (body.message or "").strip() or None

    enquiry = CareerEnquiry(
        full_name=body.full_name.strip(),
        email=body.email.strip().lower(),
        phone=phone,
        qualification=body.qualification.strip(),
        domain=body.domain.strip(),
        message=message,
        status=DEFAULT_STATUS,
    )
    db.add(enquiry)
    await db.commit()
    await db.refresh(enquiry)

    try:
        await notify_super_admins(
            db=db,
            title="New Career Program Enquiry",
            message=(
                f"New enquiry from {enquiry.full_name} ({enquiry.email}) "
                f"for {enquiry.domain}"
            ),
            type=NotificationType.general,
            related_user_id=str(enquiry.id),
        )
    except Exception as exc:
        logger.warning("Career enquiry admin notify failed (non-fatal): %s", exc)

    return _career_to_out(enquiry)


async def _list_career_rows(
    db: AsyncSession,
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
) -> List[CareerEnquiry]:
    query = select(CareerEnquiry)
    filters = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                CareerEnquiry.full_name.ilike(term),
                CareerEnquiry.email.ilike(term),
                CareerEnquiry.phone.ilike(term),
                CareerEnquiry.domain.ilike(term),
                CareerEnquiry.qualification.ilike(term),
                CareerEnquiry.message.ilike(term),
            )
        )
    if status and status.strip() and status.strip() != "all":
        filters.append(CareerEnquiry.status == status.strip())
    if domain and domain.strip() and domain.strip() != "all":
        filters.append(CareerEnquiry.domain == domain.strip())
    if qualification and qualification.strip() and qualification.strip() != "all":
        filters.append(CareerEnquiry.qualification == qualification.strip())
    if filters:
        query = query.where(*filters)
    result = await db.execute(query.order_by(CareerEnquiry.created_at.desc()))
    return list(result.scalars().all())


async def _list_contact_rows(
    db: AsyncSession,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> List[ContactInquiry]:
    query = select(ContactInquiry)
    filters = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                ContactInquiry.name.ilike(term),
                ContactInquiry.email.ilike(term),
                ContactInquiry.phone.ilike(term),
                ContactInquiry.subject.ilike(term),
                ContactInquiry.message.ilike(term),
            )
        )
    if status and status.strip() and status.strip() != "all":
        filters.append(ContactInquiry.status == status.strip())
    if filters:
        query = query.where(*filters)
    result = await db.execute(query.order_by(ContactInquiry.created_at.desc()))
    return list(result.scalars().all())


async def admin_list_career_enquiries(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
    source: Optional[str] = None,
) -> CareerEnquiryListResponse:
    source_key = (source or "all").strip().lower()
    if source_key not in {"all", "career", "contact"}:
        raise HTTPException(status_code=400, detail="Invalid source. Allowed: all, career, contact")

    # Domain / qualification only apply to Career Program rows.
    career_only_filters = bool(
        (domain and domain.strip() and domain.strip() != "all")
        or (qualification and qualification.strip() and qualification.strip() != "all")
    )

    unified: List[UnifiedEnquiryOut] = []

    include_career = source_key in {"all", "career"}
    include_contact = source_key in {"all", "contact"} and not career_only_filters

    if include_career:
        career_rows = await _list_career_rows(
            db,
            search=search,
            status=status,
            domain=domain,
            qualification=qualification,
        )
        unified.extend(_career_to_unified(row) for row in career_rows)

    if include_contact:
        contact_rows = await _list_contact_rows(db, search=search, status=status)
        unified.extend(_contact_to_unified(row) for row in contact_rows)

    unified.sort(key=lambda item: item.created_at or datetime.min, reverse=True)

    total = len(unified)
    offset = (page - 1) * page_size
    page_items = unified[offset : offset + page_size]

    return CareerEnquiryListResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
    )


async def admin_update_career_enquiry_status(
    enquiry_id: str,
    body: CareerEnquiryStatusUpdate,
    db: AsyncSession,
) -> UnifiedEnquiryOut:
    source = body.source or "career"
    raw_status = (body.status or "").strip().lower()
    has_status = bool(raw_status)
    has_notes = body.admin_notes is not None

    if not has_status and not has_notes:
        raise HTTPException(status_code=400, detail="Provide status or admin_notes")

    status = raw_status
    if has_status and status not in VALID_ENQUIRY_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {', '.join(sorted(VALID_ENQUIRY_STATUSES))}",
        )

    if source == "career":
        result = await db.execute(select(CareerEnquiry).where(CareerEnquiry.id == enquiry_id))
        enquiry = result.scalar_one_or_none()
        if not enquiry:
            raise HTTPException(status_code=404, detail="Enquiry not found")

        if has_status:
            enquiry.status = status
        if has_notes:
            enquiry.admin_notes = body.admin_notes.strip() or None
        enquiry.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(enquiry)
        return _career_to_unified(enquiry)

    result = await db.execute(select(ContactInquiry).where(ContactInquiry.id == enquiry_id))
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    if has_status:
        inquiry.status = status
    if has_notes:
        inquiry.admin_notes = body.admin_notes.strip() or None
    inquiry.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(inquiry)
    return _contact_to_unified(inquiry)
