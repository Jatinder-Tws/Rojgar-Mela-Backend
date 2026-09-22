import logging
import re
from datetime import date, datetime, time, timezone
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
    EnquiryPipelineStats,
    UnifiedEnquiryOut,
    normalize_enquiry_status,
)
from app.shared.services.notification_service import notify_super_admins

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits


def _follow_up_fields(item) -> dict:
    return {
        "admin_notes": item.admin_notes,
        "last_contact_date": item.last_contact_date,
        "next_follow_up_date": item.next_follow_up_date,
        "preferred_call_time": item.preferred_call_time,
        "interested_after_fee": item.interested_after_fee,
        "main_objection": item.main_objection,
        "final_outcome": item.final_outcome,
    }


def _career_to_out(item: CareerEnquiry) -> CareerEnquiryOut:
    return CareerEnquiryOut(
        id=item.id,
        full_name=item.full_name,
        email=item.email,
        phone=item.phone,
        qualification=item.qualification,
        domain=item.domain,
        message=item.message,
        status=normalize_enquiry_status(item.status),
        created_at=item.created_at,
        updated_at=item.updated_at,
        **_follow_up_fields(item),
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
        status=normalize_enquiry_status(item.status or DEFAULT_STATUS),
        created_at=item.created_at,
        updated_at=item.updated_at,
        **_follow_up_fields(item),
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
        status=normalize_enquiry_status(item.status or DEFAULT_CONTACT_STATUS),
        created_at=item.created_at,
        updated_at=item.updated_at,
        **_follow_up_fields(item),
    )


def _as_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    """TIMESTAMP WITHOUT TIME ZONE columns reject tz-aware values from Pydantic."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _apply_follow_up_update(row, body: CareerEnquiryStatusUpdate) -> bool:
    """Apply CRM fields that were explicitly sent in the request body."""
    fields_set = body.model_fields_set
    changed = False

    if "admin_notes" in fields_set:
        row.admin_notes = (body.admin_notes or "").strip() or None
        changed = True

    if body.clear_last_contact_date or (
        "last_contact_date" in fields_set and body.last_contact_date is None
    ):
        row.last_contact_date = None
        changed = True
    elif body.last_contact_date is not None:
        row.last_contact_date = _as_naive_utc(body.last_contact_date)
        changed = True

    if body.clear_next_follow_up_date or (
        "next_follow_up_date" in fields_set and body.next_follow_up_date is None
    ):
        row.next_follow_up_date = None
        changed = True
    elif body.next_follow_up_date is not None:
        row.next_follow_up_date = _as_naive_utc(body.next_follow_up_date)
        changed = True

    if "preferred_call_time" in fields_set:
        row.preferred_call_time = (body.preferred_call_time or "").strip() or None
        changed = True

    if "interested_after_fee" in fields_set:
        row.interested_after_fee = body.interested_after_fee or None
        changed = True

    if "main_objection" in fields_set:
        row.main_objection = (body.main_objection or "").strip() or None
        changed = True

    if "final_outcome" in fields_set:
        row.final_outcome = (body.final_outcome or "").strip() or None
        changed = True

    return changed


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


PIPELINE_STATUSES = (
    "new",
    "contacted",
    "follow_up_required",
    "visit_scheduled",
    "counselling_done",
    "converted",
    "lost",
)


def _status_match_values(status: str) -> list[str]:
    normalized = normalize_enquiry_status(status.strip())
    return {
        "follow_up_required": ["follow_up_required", "in_progress"],
        "converted": ["converted", "enrolled"],
        "lost": ["lost", "not_interested", "closed"],
    }.get(normalized, [normalized])


def _day_bounds_utc(day: Optional[date] = None) -> tuple[datetime, datetime]:
    target = day or datetime.utcnow().date()
    start = datetime.combine(target, time.min)
    end = datetime.combine(target, time.max)
    return start, end


def _career_filters(
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
    objection: Optional[str] = None,
    follow_up: Optional[str] = None,
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
                CareerEnquiry.main_objection.ilike(term),
                CareerEnquiry.admin_notes.ilike(term),
                CareerEnquiry.final_outcome.ilike(term),
                CareerEnquiry.preferred_call_time.ilike(term),
            )
        )
    if status and status.strip() and status.strip() != "all":
        filters.append(CareerEnquiry.status.in_(_status_match_values(status)))
    if domain and domain.strip() and domain.strip() != "all":
        filters.append(CareerEnquiry.domain == domain.strip())
    if qualification and qualification.strip() and qualification.strip() != "all":
        filters.append(CareerEnquiry.qualification == qualification.strip())
    if objection and objection.strip() and objection.strip() != "all":
        if objection.strip().lower() in {"none", "unset"}:
            filters.append(
                or_(CareerEnquiry.main_objection.is_(None), CareerEnquiry.main_objection == "")
            )
        else:
            filters.append(CareerEnquiry.main_objection.ilike(objection.strip()))
    if follow_up and follow_up.strip() and follow_up.strip() != "all":
        start, end = _day_bounds_utc()
        key = follow_up.strip().lower()
        if key == "today":
            filters.append(CareerEnquiry.next_follow_up_date.between(start, end))
        elif key == "overdue":
            filters.append(CareerEnquiry.next_follow_up_date < start)
        elif key == "upcoming":
            filters.append(CareerEnquiry.next_follow_up_date > end)
        elif key == "missing":
            filters.append(CareerEnquiry.next_follow_up_date.is_(None))
    return filters


def _contact_filters(
    search: Optional[str] = None,
    status: Optional[str] = None,
    objection: Optional[str] = None,
    follow_up: Optional[str] = None,
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
                ContactInquiry.main_objection.ilike(term),
                ContactInquiry.admin_notes.ilike(term),
                ContactInquiry.final_outcome.ilike(term),
                ContactInquiry.preferred_call_time.ilike(term),
            )
        )
    if status and status.strip() and status.strip() != "all":
        filters.append(ContactInquiry.status.in_(_status_match_values(status)))
    if objection and objection.strip() and objection.strip() != "all":
        if objection.strip().lower() in {"none", "unset"}:
            filters.append(
                or_(ContactInquiry.main_objection.is_(None), ContactInquiry.main_objection == "")
            )
        else:
            filters.append(ContactInquiry.main_objection.ilike(objection.strip()))
    if follow_up and follow_up.strip() and follow_up.strip() != "all":
        start, end = _day_bounds_utc()
        key = follow_up.strip().lower()
        if key == "today":
            filters.append(ContactInquiry.next_follow_up_date.between(start, end))
        elif key == "overdue":
            filters.append(ContactInquiry.next_follow_up_date < start)
        elif key == "upcoming":
            filters.append(ContactInquiry.next_follow_up_date > end)
        elif key == "missing":
            filters.append(ContactInquiry.next_follow_up_date.is_(None))
    return filters


async def _list_career_page(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    qualification: Optional[str] = None,
    objection: Optional[str] = None,
    follow_up: Optional[str] = None,
) -> Tuple[List[CareerEnquiry], int]:
    filters = _career_filters(
        search=search,
        status=status,
        domain=domain,
        qualification=qualification,
        objection=objection,
        follow_up=follow_up,
    )
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
    objection: Optional[str] = None,
    follow_up: Optional[str] = None,
) -> Tuple[List[ContactInquiry], int]:
    filters = _contact_filters(
        search=search,
        status=status,
        objection=objection,
        follow_up=follow_up,
    )
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
    objection: Optional[str] = None,
    follow_up: Optional[str] = None,
    include_contact: bool = True,
) -> CareerEnquiryListResponse:
    """Merge career + contact rows (rare path). Still paginates the merged result."""
    career_filters = _career_filters(
        search=search,
        status=status,
        domain=domain,
        qualification=qualification,
        objection=objection,
        follow_up=follow_up,
    )
    career_query = select(CareerEnquiry)
    if career_filters:
        career_query = career_query.where(*career_filters)
    career_result = await db.execute(career_query.order_by(CareerEnquiry.created_at.desc()))

    unified: List[UnifiedEnquiryOut] = [
        _career_to_unified(row) for row in career_result.scalars().all()
    ]

    if include_contact:
        contact_filters = _contact_filters(
            search=search,
            status=status,
            objection=objection,
            follow_up=follow_up,
        )
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
    objection: Optional[str] = None,
    follow_up: Optional[str] = None,
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
            objection=objection,
            follow_up=follow_up,
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
            objection=objection,
            follow_up=follow_up,
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
        objection=objection,
        follow_up=follow_up,
        include_contact=not career_only_filters,
    )


async def _count_model(db: AsyncSession, model, filters: list) -> int:
    query = select(func.count()).select_from(model)
    if filters:
        query = query.where(*filters)
    return int((await db.execute(query)).scalar() or 0)


async def admin_enquiry_pipeline_stats(
    db: AsyncSession,
    source: Optional[str] = None,
) -> EnquiryPipelineStats:
    source_key = (source or "all").strip().lower()
    if source_key not in {"all", "career", "contact"}:
        raise HTTPException(status_code=400, detail="Invalid source. Allowed: all, career, contact")

    include_career = source_key in {"all", "career"}
    include_contact = source_key in {"all", "contact"}
    start, end = _day_bounds_utc()

    by_status = {key: 0 for key in PIPELINE_STATUSES}
    total = 0
    follow_up_due_today = 0

    if include_career:
        total += await _count_model(db, CareerEnquiry, [])
        follow_up_due_today += await _count_model(
            db,
            CareerEnquiry,
            [CareerEnquiry.next_follow_up_date.between(start, end)],
        )
        for status in PIPELINE_STATUSES:
            by_status[status] += await _count_model(
                db,
                CareerEnquiry,
                [CareerEnquiry.status.in_(_status_match_values(status))],
            )

    if include_contact:
        total += await _count_model(db, ContactInquiry, [])
        follow_up_due_today += await _count_model(
            db,
            ContactInquiry,
            [ContactInquiry.next_follow_up_date.between(start, end)],
        )
        for status in PIPELINE_STATUSES:
            by_status[status] += await _count_model(
                db,
                ContactInquiry,
                [ContactInquiry.status.in_(_status_match_values(status))],
            )

    active = total - by_status.get("lost", 0)
    return EnquiryPipelineStats(
        total=total,
        active=max(active, 0),
        follow_up_due_today=follow_up_due_today,
        visit_scheduled=by_status.get("visit_scheduled", 0),
        converted=by_status.get("converted", 0),
        lost=by_status.get("lost", 0),
        by_status=by_status,
    )


async def admin_update_career_enquiry_status(
    enquiry_id: str,
    body: CareerEnquiryStatusUpdate,
    db: AsyncSession,
) -> UnifiedEnquiryOut:
    source = body.source or "career"
    raw_status = (body.status or "").strip().lower()
    has_status = bool(raw_status)
    follow_up_keys = {
        "admin_notes",
        "last_contact_date",
        "next_follow_up_date",
        "preferred_call_time",
        "interested_after_fee",
        "main_objection",
        "final_outcome",
        "clear_last_contact_date",
        "clear_next_follow_up_date",
    }
    has_follow_up = bool(body.model_fields_set & follow_up_keys) or body.clear_last_contact_date or body.clear_next_follow_up_date

    if not has_status and not has_follow_up:
        raise HTTPException(status_code=400, detail="Provide status or follow-up fields to update")

    status = normalize_enquiry_status(raw_status) if has_status else ""
    if has_status and status not in {
        "new",
        "contacted",
        "follow_up_required",
        "visit_scheduled",
        "counselling_done",
        "converted",
        "lost",
    }:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {', '.join(sorted(VALID_ENQUIRY_STATUSES - {'in_progress', 'enrolled', 'not_interested', 'closed'}))}",
        )

    if source == "career":
        result = await db.execute(select(CareerEnquiry).where(CareerEnquiry.id == enquiry_id))
        enquiry = result.scalar_one_or_none()
        if not enquiry:
            raise HTTPException(status_code=404, detail="Enquiry not found")

        if has_status:
            enquiry.status = status
        _apply_follow_up_update(enquiry, body)
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
    _apply_follow_up_update(inquiry, body)
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
