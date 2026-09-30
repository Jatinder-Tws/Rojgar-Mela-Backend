import logging
import random
import re
import secrets
import string
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import generate_otp
from app.modules.jobs_portal.models.career_enquiry import DEFAULT_STATUS, CareerEnquiry
from app.modules.jobs_portal.models.event_registration import (
    EventRegistrationForm,
    EventRegistrationPrize,
    EventRegistrationSubmission,
)
from app.modules.jobs_portal.schemas.event_registration import (
    DEFAULT_PTC_FIELDS,
    EventFormCreate,
    EventFormOut,
    EventFormPublicOut,
    EventFormUpdate,
    EventPrizeIn,
    EventPrizeOut,
    EventPrizeUpdate,
    EventRegisterPendingOut,
    EventSubmissionListResponse,
    EventSubmissionOut,
    EventTicketOut,
    EventVerifyOtpIn,
)
from app.shared.models.notification import NotificationType
from app.shared.services.celery_tasks import send_otp_email_task
from app.shared.services.notification_service import notify_super_admins
from app.shared.services.otp_redis_service import (
    PURPOSE_EMAIL_VERIFY,
    store_otp,
    verify_and_consume_otp,
)

logger = logging.getLogger(__name__)

OTP_PURPOSE = f"{PURPOSE_EMAIL_VERIFY}:event_reg"
TICKET_ALPHANUM = string.ascii_uppercase + string.digits


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return (slug[:70] or "event").rstrip("-")


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits


def _email_hint(email: str) -> str:
    local, _, domain = (email or "").partition("@")
    if not domain:
        return "***"
    shown = local[:2] if len(local) >= 2 else local[:1]
    return f"{shown}***@{domain}"


def _otp_email_key(pending_id: str) -> str:
    return f"event-reg-{pending_id}@rojgarmela.local"


def _field_dicts(fields: Any) -> List[Dict[str, Any]]:
    if not fields:
        return []
    out = []
    for item in fields:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump())
        elif isinstance(item, dict):
            out.append(item)
    return out


def _answer_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value).strip()


def _pick_answer(answers: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key in answers and _answer_text(answers.get(key)):
            return _answer_text(answers.get(key))
    return ""


def _validate_answers(fields: List[Dict[str, Any]], answers: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for field in fields:
        key = str(field.get("key") or "").strip()
        if not key:
            continue
        raw = answers.get(key)
        text = _answer_text(raw)
        required = bool(field.get("required"))
        ftype = str(field.get("type") or "text")
        label = field.get("label") or key
        if required and not text:
            raise HTTPException(status_code=400, detail=f"{label} is required")
        if not text:
            cleaned[key] = ""
            continue
        if ftype == "email":
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
                raise HTTPException(status_code=400, detail=f"Enter a valid email for {label}")
            cleaned[key] = text.lower()
        elif ftype == "phone":
            digits = _normalize_phone(text)
            if not 10 <= len(digits) <= 12:
                raise HTTPException(status_code=400, detail=f"Enter a valid 10–12 digit phone for {label}")
            cleaned[key] = digits
        elif ftype in {"select", "radio_cards"}:
            options = field.get("options") or []
            allowed = {str(opt.get("value") if isinstance(opt, dict) else getattr(opt, "value", "")) for opt in options}
            if allowed and text not in allowed:
                raise HTTPException(status_code=400, detail=f"Select a valid option for {label}")
            cleaned[key] = text
        else:
            cleaned[key] = text[:2000]
    return cleaned


def _contact_from_answers(answers: Dict[str, Any]) -> Tuple[str, str, str]:
    full_name = _pick_answer(answers, "full_name", "name")
    email = _pick_answer(answers, "email", "email_address")
    phone = _pick_answer(answers, "phone", "phone_number", "mobile")
    if len(full_name) < 2:
        raise HTTPException(status_code=400, detail="Full name is required")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=400, detail="A valid email is required")
    digits = _normalize_phone(phone)
    if not 10 <= len(digits) <= 12:
        raise HTTPException(status_code=400, detail="A valid phone number is required")
    return full_name[:150], email.lower(), digits


def _generate_ticket(prefix: str) -> str:
    p = "".join(ch for ch in (prefix or "TKT").upper() if ch.isalnum())[:6] or "TKT"
    a = "".join(secrets.choice(TICKET_ALPHANUM) for _ in range(4))
    b = "".join(secrets.choice(TICKET_ALPHANUM) for _ in range(2))
    return f"{p}-{a}-{b}"


async def _unique_ticket(db: AsyncSession, prefix: str) -> str:
    for _ in range(20):
        ticket = _generate_ticket(prefix)
        exists = await db.execute(
            select(EventRegistrationSubmission.id).where(EventRegistrationSubmission.ticket_number == ticket)
        )
        if exists.scalar_one_or_none() is None:
            enquiry_exists = await db.execute(
                select(CareerEnquiry.id).where(CareerEnquiry.ticket_number == ticket)
            )
            if enquiry_exists.scalar_one_or_none() is None:
                return ticket
    raise HTTPException(status_code=500, detail="Could not allocate a unique ticket number")


def _prize_to_out(item: EventRegistrationPrize) -> EventPrizeOut:
    return EventPrizeOut.model_validate(item)


def _form_to_out(
    item: EventRegistrationForm,
    *,
    submission_count: int = 0,
    verified_count: int = 0,
    include_prizes: bool = True,
) -> EventFormOut:
    prizes = [_prize_to_out(p) for p in (item.prizes or [])] if include_prizes else []
    return EventFormOut(
        id=item.id,
        slug=item.slug,
        event_name=item.event_name,
        booth_location=item.booth_location,
        headline=item.headline,
        subtitle=item.subtitle,
        badge_label=item.badge_label,
        cta_label=item.cta_label,
        ticket_prefix=item.ticket_prefix,
        lucky_draw_enabled=item.lucky_draw_enabled,
        is_active=item.is_active,
        fields=item.fields or [],
        thank_you_message=item.thank_you_message,
        prizes=prizes,
        submission_count=submission_count,
        verified_count=verified_count,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _form_to_public(item: EventRegistrationForm) -> EventFormPublicOut:
    return EventFormPublicOut(
        slug=item.slug,
        event_name=item.event_name,
        booth_location=item.booth_location,
        headline=item.headline,
        subtitle=item.subtitle,
        badge_label=item.badge_label,
        cta_label=item.cta_label,
        lucky_draw_enabled=item.lucky_draw_enabled,
        fields=item.fields or [],
        thank_you_message=item.thank_you_message,
    )


def _submission_to_out(item: EventRegistrationSubmission) -> EventSubmissionOut:
    return EventSubmissionOut.model_validate(item)


async def _counts_for_form(db: AsyncSession, form_id: str) -> Tuple[int, int]:
    total = int(
        (
            await db.execute(
                select(func.count()).select_from(EventRegistrationSubmission).where(
                    EventRegistrationSubmission.form_id == form_id
                )
            )
        ).scalar()
        or 0
    )
    verified = int(
        (
            await db.execute(
                select(func.count()).select_from(EventRegistrationSubmission).where(
                    EventRegistrationSubmission.form_id == form_id,
                    EventRegistrationSubmission.email_verified.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    return total, verified


async def _load_form(db: AsyncSession, form_id: str) -> EventRegistrationForm:
    result = await db.execute(
        select(EventRegistrationForm)
        .options(selectinload(EventRegistrationForm.prizes))
        .where(EventRegistrationForm.id == form_id)
    )
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Event form not found")
    return form


async def _unique_slug(db: AsyncSession, base: str, exclude_id: Optional[str] = None) -> str:
    slug = _slugify(base)
    candidate = slug
    suffix = 2
    while True:
        query = select(EventRegistrationForm.id).where(EventRegistrationForm.slug == candidate)
        if exclude_id:
            query = query.where(EventRegistrationForm.id != exclude_id)
        exists = (await db.execute(query)).scalar_one_or_none()
        if not exists:
            return candidate
        candidate = f"{slug[:60]}-{suffix}"
        suffix += 1
        if suffix > 50:
            return f"{slug[:50]}-{uuid.uuid4().hex[:6]}"


def _apply_prize_create(form_id: str, body: EventPrizeIn, sort_order: int) -> EventRegistrationPrize:
    remaining = body.remaining_inventory if body.remaining_inventory is not None else body.total_inventory
    remaining = min(max(remaining, 0), body.total_inventory)
    return EventRegistrationPrize(
        form_id=form_id,
        title=body.title.strip(),
        category=(body.category or "").strip() or None,
        worth_value=(body.worth_value or "").strip() or None,
        description=(body.description or "").strip() or None,
        total_inventory=body.total_inventory,
        remaining_inventory=remaining,
        win_weight=body.win_weight,
        voucher_expiry_days=body.voucher_expiry_days,
        redemption_instructions=(body.redemption_instructions or "").strip() or None,
        is_active=body.is_active,
        sort_order=body.sort_order if body.sort_order else sort_order,
    )


async def create_form(body: EventFormCreate, db: AsyncSession) -> EventFormOut:
    fields = _field_dicts(body.fields) or DEFAULT_PTC_FIELDS
    slug_source = body.slug or body.event_name
    slug = await _unique_slug(db, slug_source)
    form = EventRegistrationForm(
        slug=slug,
        event_name=body.event_name.strip(),
        booth_location=(body.booth_location or "").strip() or None,
        headline=body.headline.strip(),
        subtitle=(body.subtitle or "").strip() or None,
        badge_label=(body.badge_label or "").strip() or None,
        cta_label=body.cta_label.strip(),
        ticket_prefix=body.ticket_prefix,
        lucky_draw_enabled=body.lucky_draw_enabled,
        is_active=body.is_active,
        fields=fields,
        thank_you_message=(body.thank_you_message or "").strip() or None,
    )
    db.add(form)
    await db.flush()
    for index, prize in enumerate(body.prizes or []):
        db.add(_apply_prize_create(form.id, prize, index + 1))
    await db.commit()
    form = await _load_form(db, form.id)
    return _form_to_out(form, submission_count=0, verified_count=0)


async def list_forms(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> Tuple[List[EventFormOut], int]:
    filters = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                EventRegistrationForm.event_name.ilike(term),
                EventRegistrationForm.slug.ilike(term),
                EventRegistrationForm.booth_location.ilike(term),
            )
        )
    count_query = select(func.count()).select_from(EventRegistrationForm)
    query = select(EventRegistrationForm).options(selectinload(EventRegistrationForm.prizes))
    if filters:
        count_query = count_query.where(*filters)
        query = query.where(*filters)
    total = int((await db.execute(count_query)).scalar() or 0)
    result = await db.execute(
        query.order_by(EventRegistrationForm.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = list(result.scalars().unique().all())
    items: List[EventFormOut] = []
    for row in rows:
        total_subs, verified = await _counts_for_form(db, row.id)
        items.append(_form_to_out(row, submission_count=total_subs, verified_count=verified))
    return items, total


async def get_form(form_id: str, db: AsyncSession) -> EventFormOut:
    form = await _load_form(db, form_id)
    total_subs, verified = await _counts_for_form(db, form.id)
    return _form_to_out(form, submission_count=total_subs, verified_count=verified)


async def _sync_prizes(db: AsyncSession, form: EventRegistrationForm, prizes: List[EventPrizeIn]) -> None:
    existing = {prize.id: prize for prize in list(form.prizes or [])}
    kept: set[str] = set()
    for index, body in enumerate(prizes):
        if body.id and body.id in existing:
            prize = existing[body.id]
            kept.add(prize.id)
            if body.total_inventory is not None:
                delta = body.total_inventory - prize.total_inventory
                prize.total_inventory = body.total_inventory
                if body.remaining_inventory is not None:
                    prize.remaining_inventory = min(body.remaining_inventory, body.total_inventory)
                else:
                    prize.remaining_inventory = max(0, min(prize.remaining_inventory + delta, body.total_inventory))
            prize.title = body.title.strip()
            prize.category = (body.category or "").strip() or None
            prize.worth_value = (body.worth_value or "").strip() or None
            prize.description = (body.description or "").strip() or None
            prize.win_weight = body.win_weight
            prize.voucher_expiry_days = body.voucher_expiry_days
            prize.redemption_instructions = (body.redemption_instructions or "").strip() or None
            prize.is_active = body.is_active
            prize.sort_order = body.sort_order or (index + 1)
            prize.updated_at = datetime.utcnow()
        else:
            db.add(_apply_prize_create(form.id, body, index + 1))
    for prize_id, prize in existing.items():
        if prize_id not in kept:
            await db.delete(prize)


async def update_form(form_id: str, body: EventFormUpdate, db: AsyncSession) -> EventFormOut:
    form = await _load_form(db, form_id)
    data = body.model_dump(exclude_unset=True, exclude={"prizes"})
    if "slug" in data and data["slug"]:
        form.slug = await _unique_slug(db, data.pop("slug"), exclude_id=form.id)
    if "fields" in data and data["fields"] is not None:
        form.fields = _field_dicts(data.pop("fields"))
    if "prizes" in body.model_fields_set and body.prizes is not None:
        await _sync_prizes(db, form, body.prizes)
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None if key in {"booth_location", "subtitle", "badge_label", "thank_you_message"} else value.strip()
        setattr(form, key, value)
    form.updated_at = datetime.utcnow()
    await db.commit()
    form = await _load_form(db, form.id)
    total_subs, verified = await _counts_for_form(db, form.id)
    return _form_to_out(form, submission_count=total_subs, verified_count=verified)


async def delete_form(form_id: str, db: AsyncSession) -> None:
    form = await _load_form(db, form_id)
    await db.delete(form)
    await db.commit()


async def create_prize(form_id: str, body: EventPrizeIn, db: AsyncSession) -> EventPrizeOut:
    await _load_form(db, form_id)
    count = int(
        (
            await db.execute(
                select(func.count()).select_from(EventRegistrationPrize).where(
                    EventRegistrationPrize.form_id == form_id
                )
            )
        ).scalar()
        or 0
    )
    prize = _apply_prize_create(form_id, body, count + 1)
    db.add(prize)
    await db.commit()
    await db.refresh(prize)
    return _prize_to_out(prize)


async def update_prize(form_id: str, prize_id: str, body: EventPrizeUpdate, db: AsyncSession) -> EventPrizeOut:
    result = await db.execute(
        select(EventRegistrationPrize).where(
            EventRegistrationPrize.id == prize_id,
            EventRegistrationPrize.form_id == form_id,
        )
    )
    prize = result.scalar_one_or_none()
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")
    data = body.model_dump(exclude_unset=True)
    if "total_inventory" in data and "remaining_inventory" not in data:
        delta = data["total_inventory"] - prize.total_inventory
        prize.remaining_inventory = max(0, prize.remaining_inventory + delta)
        if prize.remaining_inventory > data["total_inventory"]:
            prize.remaining_inventory = data["total_inventory"]
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(prize, key, value)
    if prize.remaining_inventory > prize.total_inventory:
        prize.remaining_inventory = prize.total_inventory
    prize.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(prize)
    return _prize_to_out(prize)


async def delete_prize(form_id: str, prize_id: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(EventRegistrationPrize).where(
            EventRegistrationPrize.id == prize_id,
            EventRegistrationPrize.form_id == form_id,
        )
    )
    prize = result.scalar_one_or_none()
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")
    await db.delete(prize)
    await db.commit()


async def list_submissions(
    form_id: str,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> EventSubmissionListResponse:
    await _load_form(db, form_id)
    filters = [EventRegistrationSubmission.form_id == form_id, EventRegistrationSubmission.email_verified.is_(True)]
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                EventRegistrationSubmission.full_name.ilike(term),
                EventRegistrationSubmission.email.ilike(term),
                EventRegistrationSubmission.phone.ilike(term),
                EventRegistrationSubmission.ticket_number.ilike(term),
                EventRegistrationSubmission.prize_title.ilike(term),
            )
        )
    count_query = select(func.count()).select_from(EventRegistrationSubmission).where(*filters)
    total = int((await db.execute(count_query)).scalar() or 0)
    result = await db.execute(
        select(EventRegistrationSubmission)
        .where(*filters)
        .order_by(EventRegistrationSubmission.verified_at.desc().nullslast(), EventRegistrationSubmission.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list(result.scalars().all())
    return EventSubmissionListResponse(
        items=[_submission_to_out(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_public_form(slug: str, db: AsyncSession) -> EventFormPublicOut:
    result = await db.execute(
        select(EventRegistrationForm).where(
            EventRegistrationForm.slug == slug,
            EventRegistrationForm.is_active.is_(True),
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="This event form is not available")
    return _form_to_public(form)


async def _send_registration_otp(email: str, pending_id: str, first_name: str) -> None:
    otp_code = generate_otp()
    await store_otp(_otp_email_key(pending_id), otp_code, purpose=OTP_PURPOSE)
    send_otp_email_task.delay(email, otp_code, first_name or "there")


async def register_pending(slug: str, answers: Dict[str, Any], db: AsyncSession) -> EventRegisterPendingOut:
    result = await db.execute(
        select(EventRegistrationForm).where(
            EventRegistrationForm.slug == slug,
            EventRegistrationForm.is_active.is_(True),
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="This event form is not available")

    cleaned = _validate_answers(form.fields or DEFAULT_PTC_FIELDS, answers or {})
    full_name, email, phone = _contact_from_answers(cleaned)

    verified = await db.execute(
        select(EventRegistrationSubmission).where(
            EventRegistrationSubmission.form_id == form.id,
            EventRegistrationSubmission.email == email,
            EventRegistrationSubmission.email_verified.is_(True),
        )
    )
    if verified.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This email is already registered for this event")

    pending_result = await db.execute(
        select(EventRegistrationSubmission).where(
            EventRegistrationSubmission.form_id == form.id,
            EventRegistrationSubmission.email == email,
            EventRegistrationSubmission.email_verified.is_(False),
        )
    )
    pending = pending_result.scalar_one_or_none()
    if pending:
        pending.answers = cleaned
        pending.full_name = full_name
        pending.phone = phone
        pending.visitor_role = _pick_answer(cleaned, "visitor_role", "role") or None
        pending.organization = _pick_answer(cleaned, "organization", "college", "company") or None
        pending.interest = _pick_answer(cleaned, "interest", "program") or None
        pending.updated_at = datetime.utcnow()
    else:
        pending = EventRegistrationSubmission(
            form_id=form.id,
            answers=cleaned,
            full_name=full_name,
            email=email,
            phone=phone,
            visitor_role=_pick_answer(cleaned, "visitor_role", "role") or None,
            organization=_pick_answer(cleaned, "organization", "college", "company") or None,
            interest=_pick_answer(cleaned, "interest", "program") or None,
            email_verified=False,
        )
        db.add(pending)

    await db.commit()
    await db.refresh(pending)
    await _send_registration_otp(email, pending.id, full_name.split(" ")[0])
    return EventRegisterPendingOut(
        pending_id=pending.id,
        email_hint=_email_hint(email),
        message="We sent a verification code to your email.",
    )


async def resend_otp(slug: str, pending_id: str, db: AsyncSession) -> EventRegisterPendingOut:
    pending = await _pending_for_slug(slug, pending_id, db)
    if pending.email_verified:
        raise HTTPException(status_code=400, detail="This registration is already verified")
    await _send_registration_otp(pending.email, pending.id, pending.full_name.split(" ")[0])
    return EventRegisterPendingOut(
        pending_id=pending.id,
        email_hint=_email_hint(pending.email),
        message="A new verification code was sent to your email.",
    )


async def _pending_for_slug(slug: str, pending_id: str, db: AsyncSession) -> EventRegistrationSubmission:
    form_result = await db.execute(select(EventRegistrationForm).where(EventRegistrationForm.slug == slug))
    form = form_result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Event form not found")
    result = await db.execute(
        select(EventRegistrationSubmission).where(
            EventRegistrationSubmission.id == pending_id,
            EventRegistrationSubmission.form_id == form.id,
        )
    )
    pending = result.scalar_one_or_none()
    if not pending:
        raise HTTPException(status_code=404, detail="Registration not found")
    return pending


def _choose_prize(prizes: List[EventRegistrationPrize]) -> Optional[EventRegistrationPrize]:
    """Pick a prize by weight. Weights are treated as chances out of 100.

    If the active weights add up to less than 100, the leftover chance is a miss
    (Better luck next time) even when inventory remains.
    """
    eligible = [p for p in prizes if p.is_active and p.remaining_inventory > 0 and p.win_weight > 0]
    if not eligible:
        return None
    weights = [max(p.win_weight, 1) for p in eligible]
    total = sum(weights)
    if total < 100 and random.randint(1, 100) > total:
        return None
    return random.choices(eligible, weights=weights, k=1)[0]


async def _assign_prize(db: AsyncSession, form: EventRegistrationForm) -> Optional[EventRegistrationPrize]:
    if not form.lucky_draw_enabled:
        return None
    result = await db.execute(
        select(EventRegistrationPrize)
        .where(EventRegistrationPrize.form_id == form.id)
        .with_for_update()
    )
    prizes = list(result.scalars().all())
    prize = _choose_prize(prizes)
    if not prize:
        return None
    if prize.remaining_inventory <= 0:
        return None
    prize.remaining_inventory -= 1
    prize.updated_at = datetime.utcnow()
    return prize


def _answers_message(answers: Dict[str, Any]) -> str:
    lines = []
    for key, value in answers.items():
        text = _answer_text(value)
        if not text:
            continue
        label = key.replace("_", " ").title()
        lines.append(f"{label}: {text}")
    return "\n".join(lines)[:2000]


async def verify_otp(slug: str, body: EventVerifyOtpIn, db: AsyncSession) -> EventTicketOut:
    pending = await _pending_for_slug(slug, body.pending_id, db)
    form_result = await db.execute(
        select(EventRegistrationForm)
        .options(selectinload(EventRegistrationForm.prizes))
        .where(EventRegistrationForm.id == pending.form_id)
    )
    form = form_result.scalar_one()

    if pending.email_verified and pending.ticket_number:
        return _ticket_payload(pending, form)

    ok = await verify_and_consume_otp(_otp_email_key(pending.id), body.otp.strip(), purpose=OTP_PURPOSE)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    prize = await _assign_prize(db, form)
    ticket = await _unique_ticket(db, form.ticket_prefix)
    now = datetime.utcnow()

    pending.email_verified = True
    pending.verified_at = now
    pending.ticket_number = ticket
    pending.updated_at = now
    if prize:
        pending.prize_id = prize.id
        pending.prize_title = prize.title
        pending.prize_category = prize.category
        pending.prize_worth = prize.worth_value
        pending.redemption_instructions = prize.redemption_instructions
        pending.is_winner = True
    else:
        pending.prize_title = "Better luck next time" if form.lucky_draw_enabled else None
        pending.is_winner = False

    role = pending.visitor_role or pending.interest or "Event visitor"
    enquiry = CareerEnquiry(
        full_name=pending.full_name,
        email=pending.email,
        phone=pending.phone,
        qualification=pending.organization or "Event visitor",
        domain=pending.interest or role,
        message=_answers_message(pending.answers or {}),
        status=DEFAULT_STATUS,
        consent_to_contact=True,
        event_name=form.event_name,
        ticket_number=ticket,
        prize_title=pending.prize_title,
        event_form_id=form.id,
    )
    db.add(enquiry)
    await db.flush()
    pending.enquiry_id = enquiry.id
    await db.commit()
    await db.refresh(pending)

    try:
        await notify_super_admins(
            db=db,
            title="New event stall registration",
            message=(
                f"{pending.full_name} registered for {form.event_name} "
                f"(ticket {ticket})"
            ),
            type=NotificationType.general,
            related_user_id=str(enquiry.id),
        )
    except Exception as exc:
        logger.warning("Event registration admin notify failed (non-fatal): %s", exc)

    return _ticket_payload(pending, form)


def _ticket_payload(pending: EventRegistrationSubmission, form: EventRegistrationForm) -> EventTicketOut:
    prize_description = None
    if pending.prize_id:
        for prize in form.prizes or []:
            if prize.id == pending.prize_id:
                prize_description = prize.description
                break
    return EventTicketOut(
        pending_id=pending.id,
        ticket_number=pending.ticket_number or "",
        event_name=form.event_name,
        booth_location=form.booth_location,
        full_name=pending.full_name,
        email=pending.email,
        lucky_draw_enabled=form.lucky_draw_enabled,
        is_winner=pending.is_winner,
        prize_title=pending.prize_title,
        prize_category=pending.prize_category,
        prize_worth=pending.prize_worth,
        prize_description=prize_description,
        redemption_instructions=pending.redemption_instructions,
        thank_you_message=form.thank_you_message,
    )


async def test_draw(form_id: str, db: AsyncSession) -> Dict[str, Any]:
    form = await _load_form(db, form_id)
    if not form.lucky_draw_enabled:
        return {"prize_title": None, "prize_category": None, "remaining_inventory": None, "message": "Lucky draw is disabled for this form"}
    prize = _choose_prize(form.prizes or [])
    if not prize:
        return {
            "prize_title": "Better luck next time",
            "prize_category": None,
            "remaining_inventory": 0,
            "message": "No active prizes with remaining inventory. This is a dry run — inventory was not changed.",
        }
    return {
        "prize_title": prize.title,
        "prize_category": prize.category,
        "remaining_inventory": prize.remaining_inventory,
        "message": "Dry run only — inventory was not changed.",
    }
