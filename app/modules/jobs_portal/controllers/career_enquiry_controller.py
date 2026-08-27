import logging
import re
from datetime import datetime
from typing import List, Optional, Tuple

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


def _career_filters(
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
) -> list:
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
    return filters


def _contact_filters(
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
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
    return filters


async def _list_career_page(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
) -> Tuple[List[CareerEnquiry], int]:
    filters = _career_filters(search=search, status=status, domain=domain, qualification=qualification)
    count_query = select(func.count()).select_from(CareerEnquiry)
    query = select(CareerEnquiry)
    if filters:
        count_query = count_query.where(*filters)
        query = query.where(*filters)

    total = int((await db.execute(count_query)).scalar() or 0)
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(CareerEnquiry.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def _list_contact_page(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[ContactInquiry], int]:
    filters = _contact_filters(search=search, status=status)
    count_query = select(func.count()).select_from(ContactInquiry)
    query = select(ContactInquiry)
    if filters:
        count_query = count_query.where(*filters)
        query = query.where(*filters)

    total = int((await db.execute(count_query)).scalar() or 0)
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(ContactInquiry.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def _list_all_merged(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
    include_contact: bool = True,
) -> CareerEnquiryListResponse:
    """Merge career + contact rows (rare path). Still paginates the merged result."""
    career_filters = _career_filters(
        search=search, status=status, domain=domain, qualification=qualification
    )
    career_query = select(CareerEnquiry)
    if career_filters:
        career_query = career_query.where(*career_filters)
    career_result = await db.execute(career_query.order_by(CareerEnquiry.created_at.desc()))

    unified: List[UnifiedEnquiryOut] = [
        _career_to_unified(row) for row in career_result.scalars().all()
    ]

    if include_contact:
        contact_filters = _contact_filters(search=search, status=status)
        contact_query = select(ContactInquiry)
        if contact_filters:
            contact_query = contact_query.where(*contact_filters)
        contact_result = await db.execute(contact_query.order_by(ContactInquiry.created_at.desc()))
        unified.extend(_contact_to_unified(row) for row in contact_result.scalars().all())

    unified.sort(key=lambda item: item.created_at or datetime.min, reverse=True)
    total = len(unified)
    offset = (page - 1) * page_size
    return CareerEnquiryListResponse(
        items=unified[offset : offset + page_size],
        total=total,
        page=page,
        page_size=page_size,
    )


async def admin_list_career_enquiries(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
    source: Optional[str] = None,
) -> CareerEnquiryListResponse:
    source_key = (source or "career").strip().lower()
    if source_key not in {"all", "career", "contact"}:
        raise HTTPException(status_code=400, detail="Invalid source. Allowed: all, career, contact")

    # Domain / qualification only apply to Career Program rows.
    career_only_filters = bool(
        (domain and domain.strip() and domain.strip() != "all")
        or (qualification and qualification.strip() and qualification.strip() != "all")
    )

    # Single-source paths use DB-level OFFSET/LIMIT (frontend always sends career|contact).
    if source_key == "career":
        rows, total = await _list_career_page(
            db,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            domain=domain,
            qualification=qualification,
        )
        return CareerEnquiryListResponse(
            items=[_career_to_unified(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    if source_key == "contact":
        if career_only_filters:
            return CareerEnquiryListResponse(items=[], total=0, page=page, page_size=page_size)
        rows, total = await _list_contact_page(
            db,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
        )
        return CareerEnquiryListResponse(
            items=[_contact_to_unified(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    return await _list_all_merged(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        domain=domain,
        qualification=qualification,
        include_contact=not career_only_filters,
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


async def admin_delete_enquiry(
    enquiry_id: str,
    source: str,
    db: AsyncSession,
) -> None:
    source_key = (source or "career").strip().lower()
    if source_key not in {"career", "contact"}:
        raise HTTPException(status_code=400, detail="Invalid source. Allowed: career, contact")

    if source_key == "career":
        result = await db.execute(select(CareerEnquiry).where(CareerEnquiry.id == enquiry_id))
        enquiry = result.scalar_one_or_none()
        if not enquiry:
            raise HTTPException(status_code=404, detail="Enquiry not found")
        await db.delete(enquiry)
        await db.commit()
        return

    result = await db.execute(select(ContactInquiry).where(ContactInquiry.id == enquiry_id))
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    await db.delete(inquiry)
    await db.commit()
