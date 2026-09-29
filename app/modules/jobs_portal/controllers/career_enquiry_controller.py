import logging
import re
import uuid
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
    AdminManualEnquiryCreate,
    CareerEnquiryCreate,
    CareerEnquiryListResponse,
    CareerEnquiryOut,
    CareerEnquiryStatusUpdate,
    EnquiryImportResult,
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
        consent_to_contact=item.consent_to_contact,
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


async def admin_get_enquiry(enquiry_id: str, db: AsyncSession) -> UnifiedEnquiryOut:
    try:
        enquiry_id = str(uuid.UUID(enquiry_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Enquiry not found")

    career_result = await db.execute(select(CareerEnquiry).where(CareerEnquiry.id == enquiry_id))
    career_enquiry = career_result.scalar_one_or_none()
    if career_enquiry:
        return _career_to_unified(career_enquiry)

    contact_result = await db.execute(select(ContactInquiry).where(ContactInquiry.id == enquiry_id))
    contact_enquiry = contact_result.scalar_one_or_none()
    if contact_enquiry:
        return _contact_to_unified(contact_enquiry)

    raise HTTPException(status_code=404, detail="Enquiry not found")


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


_STATUS_LABELS = {
    "new": "new",
    "new lead": "new",
    "open": "new",
    "pending": "new",
    "contacted": "contacted",
    "not picked": "contacted",
    "call not picked": "contacted",
    "follow up required": "follow_up_required",
    "follow-up required": "follow_up_required",
    "follow_up_required": "follow_up_required",
    "visit scheduled": "visit_scheduled",
    "visit_scheduled": "visit_scheduled",
    "counselling done": "counselling_done",
    "counselling_done": "counselling_done",
    "hybrid training": "follow_up_required",
    "converted": "converted",
    "enrolled": "converted",
    "lost": "lost",
    "in progress": "follow_up_required",
    "in_progress": "follow_up_required",
    "not interested": "lost",
    "not_interested": "lost",
    "not intersted": "lost",
    "not-interested": "lost",
    "not_intersted": "lost",
    "call not picked /not interested": "lost",
    "call not picked / not interested": "lost",
    "closed": "lost",
    "invalid": "lost",
}

_HEADER_ALIASES = {
    "first_name": ("first_name", "firstname", "first"),
    "last_name": ("last_name", "lastname", "last"),
    "full_name": ("full_name", "name", "candidate_name", "student_name", "lead_name", "client_name"),
    "phone": ("phone", "phone_number", "mobile", "mobile_number", "mobile_no", "contact_number", "contact_no", "contact", "number", "tel"),
    "email": ("email", "email_address", "mail", "mail_id", "email_id"),
    "city": ("city", "location", "address", "state"),
    "preferred_contact": ("preferred_contact", "preferred_contact_mode"),
    "programme": ("programme", "programme_of_interest", "program", "domain", "course", "area_of_interest", "field"),
    "lead_source": ("lead_source", "source", "source_name", "channel"),
    "enquiry_date": ("enquiry_date", "inquiry_date", "date", "lead_date", "created_date", "created_at"),
    "campaign_code": ("campaign_code", "campaign", "campaign_referral_code", "referral_code"),
    "message": ("message", "initial_enquiry_message", "enquiry_message", "inquiry_message", "details"),
    "status": ("status", "stage", "candidate_status", "lead_status", "current_status", "call_status"),
    "assigned_counsellor": ("assigned_counsellor", "counsellor", "counselor", "owner", "responsible_person", "responsible", "assigned_to", "assigned_person", "caller"),
    "priority": ("priority",),
    "next_follow_up_date": ("next_follow_up_date", "follow_up_date", "next_followup_date", "next_followup", "next_touch"),
    "last_contact_date": ("last_follow_up_taken", "last_followup_taken", "last_follow_up", "last_followup", "last_contact_date", "last_touch", "last_call_date"),
    "follow_ups_taken": ("follow_ups_taken", "followups_taken", "follow_up_taken", "follow_ups", "followups", "call_count"),
    "follow_up_time": ("follow_up_time", "time"),
    "follow_up_mode": ("follow_up_mode", "mode"),
    "follow_up_note": ("follow_up_note", "note", "notes"),
    "remarks": ("remarks", "final_remarks", "outcome", "remark", "reason", "comment", "comments", "feedback"),
}


def _parse_loose_date(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat", "0"}:
        return None

    # Handle common short typos like 24-08-206 -> 24-08-2026
    text = re.sub(r"-20(\d)$", r"-202\1", text)
    text = re.sub(r"/20(\d)$", r"/202\1", text)

    candidates = [text, text[:10], text[:19]]
    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%y %H:%M:%S",
    )
    for candidate in candidates:
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    try:
        return datetime.fromisoformat(text.replace("Z", ""))
    except ValueError:
        return None


def _resolve_status(raw: Optional[str]) -> str:
    text = (raw or "new").strip().lower().replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    mapped = _STATUS_LABELS.get(text) or _STATUS_LABELS.get(text.replace(" ", "_"))
    if mapped:
        return mapped
    try:
        normalized = normalize_enquiry_status(raw)
        if normalized in {"new", "contacted", "follow_up_required", "visit_scheduled", "counselling_done", "converted", "lost"}:
            return normalized
    except Exception:
        pass
    if "not" in text and "interest" in text:
        return "lost"
    return "new"


def _compose_manual_enquiry(data: dict) -> CareerEnquiry:
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    full_name = (data.get("full_name") or f"{first} {last}").strip()
    if len(full_name) < 2:
        raise ValueError("Name is required")
    if len(full_name) > 150:
        full_name = full_name[:150]

    phone = _normalize_phone(data.get("phone") or "")
    if len(phone) < 7 or len(phone) > 15:
        raise ValueError("Phone must be 7–15 digits")

    email = (data.get("email") or "").strip().lower()
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(email) > 150:
        # Generate safe placeholder email when missing from spreadsheet
        clean_name = re.sub(r"[^a-z0-9]", "", full_name.lower()) or "lead"
        clean_digits = phone or "0000000"
        email = f"{clean_name[:12]}.{clean_digits[-6:]}@lead.rojgarmela.ai"

    programme = (data.get("programme") or "").strip() or "General enquiry"
    city = (data.get("city") or "").strip()
    lead_source = (data.get("lead_source") or "").strip()
    qualification = " · ".join(part for part in (city, lead_source) if part) or "Manual entry"
    qualification = qualification[:100]

    extras = []
    preferred = (data.get("preferred_contact") or "").strip()
    campaign = (data.get("campaign_code") or "").strip()
    counsellor = (data.get("assigned_counsellor") or "").strip()
    priority = (data.get("priority") or "").strip()
    mode = (data.get("follow_up_mode") or "").strip()
    follow_ups_taken = str(data.get("follow_ups_taken") or "").strip()
    if follow_ups_taken and follow_ups_taken not in {"nan", "None", "0"}:
        extras.append(f"Follow-ups taken: {follow_ups_taken}")
    if preferred:
        extras.append(f"Preferred contact: {preferred}")
    if campaign:
        extras.append(f"Campaign / referral: {campaign}")
    if counsellor:
        extras.append(f"Assigned counsellor: {counsellor}")
    if priority:
        extras.append(f"Priority: {priority}")

    message = (data.get("message") or "").strip()
    if extras:
        message = f"{message}\n\n{chr(10).join(extras)}".strip() if message else "\n".join(extras)
    message = message[:4000] or None

    follow_time = (data.get("follow_up_time") or "").strip()
    call_time = " · ".join(part for part in (follow_time, mode) if part) or None
    if call_time:
        call_time = call_time[:120]

    note = (data.get("follow_up_note") or "").strip()
    if counsellor and note:
        note = f"Counsellor: {counsellor}\n{note}"
    elif counsellor:
        note = f"Counsellor: {counsellor}"

    raw_enquiry_date = data.get("enquiry_date")
    enquiry_at = _parse_loose_date(raw_enquiry_date)
    if raw_enquiry_date and enquiry_at is None:
        enquiry_at = datetime.utcnow()
    enquiry_at = enquiry_at or datetime.utcnow()

    raw_last_contact = data.get("last_contact_date")
    last_contact_at = _parse_loose_date(raw_last_contact)

    raw_follow_date = data.get("next_follow_up_date")
    follow_at = _parse_loose_date(raw_follow_date)

    return CareerEnquiry(
        full_name=full_name,
        email=email,
        phone=phone,
        qualification=qualification,
        domain=programme[:150],
        message=message,
        status=_resolve_status(data.get("status")),
        admin_notes=note[:5000] or None,
        last_contact_date=last_contact_at,
        next_follow_up_date=follow_at,
        preferred_call_time=call_time,
        final_outcome=((data.get("remarks") or "").strip()[:2000] or None),
        consent_to_contact=data.get("consent_to_contact") is True,
        created_at=enquiry_at,
        updated_at=datetime.utcnow(),
    )


async def _load_duplicate_keys(db: AsyncSession) -> tuple[set[str], set[str]]:
    emails: set[str] = set()
    phones: set[str] = set()
    career_rows = await db.execute(select(CareerEnquiry.email, CareerEnquiry.phone))
    contact_rows = await db.execute(select(ContactInquiry.email, ContactInquiry.phone))
    for email, phone in list(career_rows.all()) + list(contact_rows.all()):
        if email:
            emails.add(email.strip().lower())
        digits = _normalize_phone(phone or "")
        if digits:
            phones.add(digits)
    return emails, phones


async def admin_create_enquiry(
    body: AdminManualEnquiryCreate,
    db: AsyncSession,
) -> UnifiedEnquiryOut:
    try:
        enquiry = _compose_manual_enquiry(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.check_duplicates:
        emails, phones = await _load_duplicate_keys(db)
        if enquiry.email in emails or enquiry.phone in phones:
            raise HTTPException(
                status_code=409,
                detail="A lead with this phone or email already exists",
            )

    db.add(enquiry)
    await db.commit()
    await db.refresh(enquiry)
    return _career_to_unified(enquiry)


def enquiry_import_template():
    import io

    import pandas as pd
    from fastapi.responses import StreamingResponse

    sample = pd.DataFrame(
        [
            {
                "Date": "2026-08-26",
                "Name": "Gurpreet Singh",
                "Phone Number": "9878756966",
                "Candidate Status": "Not Interested",
                "Follow-ups Taken": "3",
                "Last Follow -up Taken": "2026-08-26",
                "Final Remarks": "Call Not Picked / Not Interested",
                "Responsible Person": "Pankaj",
            }
        ]
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="Enquiries")
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="enquiries-import-template.xlsx"'},
    )


def _normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")


def _find_header_and_prepare_df(raw_df):
    import pandas as pd

    if raw_df is None or raw_df.empty:
        return raw_df

    key_terms = ("name", "phone", "mobile", "contact", "candidate", "student", "status", "date", "remark", "person", "sr_no")

    # Clean existing columns
    raw_cols = [_normalize_header(c) for c in raw_df.columns]
    matches = sum(1 for c in raw_cols if any(k in c for k in key_terms))

    if matches >= 2:
        # Deduplicate column names
        unique_cols = []
        seen = {}
        for idx, col in enumerate(raw_cols):
            base = col or f"col_{idx}"
            seen[base] = seen.get(base, 0) + 1
            unique_cols.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
        raw_df.columns = unique_cols
        return raw_df

    # Search top 25 rows for header row
    for r_idx in range(min(25, len(raw_df))):
        row_vals = [_normalize_header(v) for v in raw_df.iloc[r_idx].values]
        row_matches = sum(1 for v in row_vals if any(k in v for k in key_terms))
        if row_matches >= 2:
            new_df = raw_df.iloc[r_idx + 1:].copy()
            unique_cols = []
            seen = {}
            for c_idx, col in enumerate(row_vals):
                base = col or f"col_{c_idx}"
                seen[base] = seen.get(base, 0) + 1
                unique_cols.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
            new_df.columns = unique_cols
            return new_df

    # Fallback deduplication
    unique_cols = []
    seen = {}
    for idx, col in enumerate(raw_cols):
        base = col or f"col_{idx}"
        seen[base] = seen.get(base, 0) + 1
        unique_cols.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    raw_df.columns = unique_cols
    return raw_df


def _clean_str_val(v) -> str:
    if v is None:
        return ""
    text = str(v).strip()
    if text.lower() in {"nan", "none", "nat", "<na>", "null"}:
        return ""
    # Normalize floats like '9878756966.0' -> '9878756966'
    if re.match(r"^\d+\.0+$", text):
        text = text.split(".")[0]
    return text


def _cell_smart(row: dict, field_name: str, *aliases: str) -> str:
    # 1. Exact alias match
    for key in aliases:
        if key in row:
            text = _clean_str_val(row[key])
            if text:
                return text

    # 2. Fuzzy substring key match
    for k, v in row.items():
        text = _clean_str_val(v)
        if not text:
            continue

        clean_k = _normalize_header(k)

        if field_name == "phone":
            if any(w in clean_k for w in ("phone", "mobile", "contact", "whatsapp", "calling", "tel")) and not any(x in clean_k for x in ("sr", "serial", "reg", "roll", "count")):
                return text
        elif field_name in ("full_name", "first_name"):
            if any(w in clean_k for w in ("name", "candidate", "student", "client", "lead")) and not any(x in clean_k for x in ("responsible", "counsel", "status", "user_id")):
                return text
        elif field_name == "status":
            if any(w in clean_k for w in ("status", "stage", "state", "lead_status")):
                return text
        elif field_name == "assigned_counsellor":
            if any(w in clean_k for w in ("responsible", "counsellor", "counselor", "owner", "assigned", "caller")):
                return text
        elif field_name == "remarks":
            if any(w in clean_k for w in ("remark", "outcome", "reason", "comment", "feedback", "notes")):
                return text
        elif field_name == "enquiry_date":
            if ("date" in clean_k or "time" in clean_k) and not any(x in clean_k for x in ("last", "follow", "next")):
                return text
        elif field_name == "last_contact_date":
            if ("last" in clean_k and "follow" in clean_k) or ("last_contact" in clean_k) or ("last_call" in clean_k):
                return text
        elif field_name == "follow_ups_taken":
            if ("follow" in clean_k and "taken" in clean_k) or ("followup" in clean_k and "count" in clean_k) or ("call_count" in clean_k):
                return text

    # 3. Value-based fallback for phone
    if field_name == "phone":
        for k, v in row.items():
            text = _clean_str_val(v)
            if not text:
                continue
            clean_k = _normalize_header(k)
            if any(x in clean_k for x in ("sr", "serial", "index", "count", "follow")):
                continue
            digits = _normalize_phone(text)
            if 10 <= len(digits) <= 12:
                return digits

    return ""


async def _load_supervisor_map(db: AsyncSession) -> dict[str, str]:
    """Map first name, last name, full name, and email prefix to canonical name."""
    supervisor_map: dict[str, str] = {}
    try:
        user_rows = await db.execute(
            select(User.first_name, User.last_name, User.email)
            .where(or_(User.is_super_admin == True, User.role == "supervisor"))
        )
        for fn, ln, em in user_rows.all():
            first = (fn or "").strip()
            last = (ln or "").strip()
            full = f"{first} {last}".strip() or (em or "").split("@")[0]
            if first:
                supervisor_map[first.lower()] = full
            if last:
                supervisor_map[last.lower()] = full
            if full:
                supervisor_map[full.lower()] = full
            if em:
                supervisor_map[em.split("@")[0].strip().lower()] = full
    except Exception as exc:
        logger.warning("Could not build supervisor map: %s", exc)

    return supervisor_map


async def admin_import_enquiries(file, db: AsyncSession) -> EnquiryImportResult:
    import io
    import pandas as pd

    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Upload an Excel (.xlsx, .xls) or CSV file")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The file is empty")

    frames: list[tuple[str, pd.DataFrame]] = []
    try:
        if filename.endswith(".csv"):
            text = content.decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(text), dtype=str)
            frames.append(("default", df))
        else:
            excel_data = pd.read_excel(io.BytesIO(content), sheet_name=None, dtype=str)
            for sheet_name, df in excel_data.items():
                if df is not None and not df.empty:
                    frames.append((str(sheet_name), df))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read the file: {exc}") from exc

    if not frames:
        raise HTTPException(status_code=400, detail="The file has no data rows")

    emails, phones = await _load_duplicate_keys(db)
    supervisor_map = await _load_supervisor_map(db)

    created = 0
    skipped = 0
    failed = 0
    errors: list[str] = []

    for sheet_name, frame in frames:
        if frame.empty:
            continue

        frame = _find_header_and_prepare_df(frame)
        rows = frame.where(pd.notnull(frame), None).to_dict("records")

        sheet_clean = str(sheet_name).strip()
        sheet_source = sheet_clean if sheet_clean and sheet_clean.lower() not in {"sheet1", "default", "enquiries"} else "Excel Import"

        for index, row in enumerate(rows, start=2):
            payload = {
                field: _cell_smart(row, field, *aliases) for field, aliases in _HEADER_ALIASES.items()
            }
            # If neither name nor phone nor email found, skip empty/spacer row
            if not any(payload.get(key) for key in ("first_name", "last_name", "full_name", "phone", "email")):
                continue

            # Set sheet name as Lead Source name in DB
            if not payload.get("lead_source"):
                payload["lead_source"] = sheet_source
            if not payload.get("programme"):
                payload["programme"] = sheet_source

            # Match responsible person / counsellor name if available
            raw_counsellor = (payload.get("assigned_counsellor") or "").strip()
            if raw_counsellor:
                matched = supervisor_map.get(raw_counsellor.lower())
                if matched:
                    payload["assigned_counsellor"] = matched
                else:
                    # User rule: if name matches auto-assign, else skip assigning
                    payload["assigned_counsellor"] = ""

            try:
                enquiry = _compose_manual_enquiry(payload)
            except ValueError as exc:
                failed += 1
                if len(errors) < 25:
                    errors.append(f"Sheet '{sheet_name}' Row {index}: {exc}")
                continue

            if enquiry.phone in phones:
                skipped += 1
                if len(errors) < 25:
                    errors.append(f"Sheet '{sheet_name}' Row {index}: duplicate phone ({enquiry.phone}), skipped")
                continue

            phones.add(enquiry.phone)
            emails.add(enquiry.email)
            db.add(enquiry)
            created += 1

    if created:
        await db.commit()

    return EnquiryImportResult(created=created, skipped=skipped, failed=failed, errors=errors)


