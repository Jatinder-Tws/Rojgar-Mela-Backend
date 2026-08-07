import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.career_enquiry import DEFAULT_STATUS, CareerEnquiry
from models.notification import NotificationType
from schemas.career_enquiry import (
    VALID_ENQUIRY_STATUSES,
    CareerEnquiryCreate,
    CareerEnquiryListResponse,
    CareerEnquiryOut,
    CareerEnquiryStatusUpdate,
)
from services.notification_service import notify_super_admins

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits


def _to_out(item: CareerEnquiry) -> CareerEnquiryOut:
    return CareerEnquiryOut(
        id=item.id,
        full_name=item.full_name,
        email=item.email,
        phone=item.phone,
        qualification=item.qualification,
        domain=item.domain,
        status=item.status,
        admin_notes=item.admin_notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def create_career_enquiry(body: CareerEnquiryCreate, db: AsyncSession) -> CareerEnquiryOut:
    phone = _normalize_phone(body.phone)
    if len(phone) < 10 or len(phone) > 12:
        raise HTTPException(status_code=400, detail="Enter a valid 10–12 digit phone number")

    enquiry = CareerEnquiry(
        full_name=body.full_name.strip(),
        email=body.email.strip().lower(),
        phone=phone,
        qualification=body.qualification.strip(),
        domain=body.domain.strip(),
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

    return _to_out(enquiry)


async def admin_list_career_enquiries(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
) -> CareerEnquiryListResponse:
    query = select(CareerEnquiry)
    count_query = select(func.count()).select_from(CareerEnquiry)

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
        count_query = count_query.where(*filters)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(CareerEnquiry.created_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return CareerEnquiryListResponse(
        items=[_to_out(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


async def admin_update_career_enquiry_status(
    enquiry_id: str,
    body: CareerEnquiryStatusUpdate,
    db: AsyncSession,
) -> CareerEnquiryOut:
    status = (body.status or "").strip().lower()
    if status not in VALID_ENQUIRY_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {', '.join(sorted(VALID_ENQUIRY_STATUSES))}",
        )

    result = await db.execute(select(CareerEnquiry).where(CareerEnquiry.id == enquiry_id))
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    enquiry.status = status
    if body.admin_notes is not None:
        enquiry.admin_notes = body.admin_notes.strip() or None
    enquiry.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(enquiry)
    return _to_out(enquiry)
