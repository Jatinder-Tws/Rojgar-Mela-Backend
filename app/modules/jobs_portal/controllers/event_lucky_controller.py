import hashlib
import json
import logging
import re
import secrets
import uuid
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis.asyncio as aioredis

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_upload_dir, settings
from app.core.security import generate_otp, generate_secure_password, hash_password
from app.modules.jobs_portal.models.career_enquiry import DEFAULT_STATUS, CareerEnquiry
from app.modules.jobs_portal.models.event_lucky import EventLuckyDraw, EventLuckyEntry
from app.modules.jobs_portal.models.site_announcement import SiteAnnouncement
from app.shared.models.user import CompanyType, User, UserRole
from app.shared.services.celery_tasks import send_otp_email_task
from app.shared.services.email_service import send_password_email
from app.shared.services.otp_redis_service import PURPOSE_EMAIL_VERIFY, store_otp, verify_and_consume_otp

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
OTP_PURPOSE = f"{PURPOSE_EMAIL_VERIFY}:lucky_event"


def ist_now() -> datetime:
    return datetime.now(IST)


def ist_today() -> str:
    return ist_now().strftime("%Y-%m-%d")


async def _ensure_account(entry: EventLuckyEntry, db: AsyncSession) -> Optional[tuple]:
    result = await db.execute(select(User).where(User.email == entry.email))
    if result.scalar_one_or_none():
        return None
    parts = (entry.full_name or "Guest").split()
    first_name = parts[0][:50]
    last_name = " ".join(parts[1:])[:50]
    password = generate_secure_password()
    role = UserRole.seeker if entry.role == "seeker" else UserRole.provider
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=entry.email,
        phone=(entry.phone or "")[:15],
        hashed_password=hash_password(password),
        role=role,
        is_verified=True,
        onboarding_complete=False,
        is_first_login=True,
        totp_enabled=False,
    )
    if role == UserRole.provider:
        user.company_name = (entry.organization or "")[:200]
        user.company_location = (entry.location or "")[:200]
        user.company_type = CompanyType.company
    db.add(user)
    await db.flush()
    return password, first_name, role.value


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return (slug[:70] or "event").rstrip("-")


async def unique_lucky_slug(db: AsyncSession, title: str, exclude_id: Optional[str] = None) -> str:
    base = _slugify(title)
    candidate = base
    n = 2
    while True:
        query = select(SiteAnnouncement.id).where(SiteAnnouncement.lucky_draw_slug == candidate)
        if exclude_id:
            query = query.where(SiteAnnouncement.id != exclude_id)
        if (await db.execute(query)).scalar_one_or_none() is None:
            return candidate
        candidate = f"{base[:60]}-{n}"
        n += 1


def event_span(event: SiteAnnouncement) -> tuple[str, str]:
    days = max(int(event.lucky_draw_days or 1), 1)
    start = event.start_date or event.event_date
    if start is None:
        today = datetime.strptime(ist_today(), "%Y-%m-%d").date()
        return today.isoformat(), (today + timedelta(days=days - 1)).isoformat()
    start_day = start.date() if hasattr(start, "date") else start
    return start_day.isoformat(), (start_day + timedelta(days=days - 1)).isoformat()


def event_day_index(event: SiteAnnouncement, day: str) -> Optional[int]:
    start = event.start_date or event.event_date
    if start is None:
        return 0
    start_day = start.date() if hasattr(start, "date") else start
    target = datetime.strptime(day, "%Y-%m-%d").date()
    delta = (target - start_day).days
    days = max(int(event.lucky_draw_days or 1), 1)
    if delta < 0 or delta >= days:
        return None
    return delta


def reveal_at(event: SiteAnnouncement, day: str) -> datetime:
    raw = (event.lucky_draw_reveal_time or "18:00").strip()
    try:
        hour, minute = [int(part) for part in raw.split(":")[:2]]
    except ValueError:
        hour, minute = 18, 0
    hour = min(max(hour, 0), 23)
    minute = min(max(minute, 0), 59)
    date = datetime.strptime(day, "%Y-%m-%d").date()
    return datetime(date.year, date.month, date.day, hour, minute, tzinfo=IST)


def registration_window(event: SiteAnnouncement, now: Optional[datetime] = None) -> dict:
    """Decide which day's pool a signup belongs to.

    Before the daily result time, the ticket is in today's draw.
    After that time, it moves to the next event day.
    On the last day after the result time, signup is allowed but the draw is over.
    Outside the event dates, the form is closed.
    """
    moment = now or ist_now()
    today = moment.strftime("%Y-%m-%d")
    starts_on, ends_on = event_span(event)
    days = max(int(event.lucky_draw_days or 1), 1)
    index = event_day_index(event, today)
    live = bool(event.is_active and event.lucky_draw_enabled)
    closed = {
        "registration_open": False,
        "registration_bucket": "closed" if today > ends_on or not live else "not_started",
        "assigned_draw_date": None,
        "draw_eligible": False,
    }
    if not live or index is None:
        if today < starts_on:
            closed["registration_bucket"] = "not_started"
        return closed
    if moment < reveal_at(event, today):
        return {
            "registration_open": True,
            "registration_bucket": "today",
            "assigned_draw_date": today,
            "draw_eligible": True,
        }
    if index < days - 1:
        next_day = (datetime.strptime(today, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()
        return {
            "registration_open": True,
            "registration_bucket": "next_day",
            "assigned_draw_date": next_day,
            "draw_eligible": True,
        }
    return {
        "registration_open": True,
        "registration_bucket": "draw_closed",
        "assigned_draw_date": today,
        "draw_eligible": False,
    }


def public_payload(event: SiteAnnouncement, today: Optional[str] = None) -> dict:
    day = today or ist_today()
    reveal = reveal_at(event, day)
    now = ist_now()
    day_index = event_day_index(event, day)
    starts_on, ends_on = event_span(event)
    window = registration_window(event, now)
    return {
        "slug": event.lucky_draw_slug,
        "title": event.title or "Event",
        "text": event.text,
        "location": event.event_location,
        "organizer": event.organizer,
        "starts_on": starts_on,
        "ends_on": ends_on,
        "days": max(int(event.lucky_draw_days or 1), 1),
        "reveal_time": event.lucky_draw_reveal_time or "18:00",
        "today": day,
        "day_index": day_index,
        "registration_open": window["registration_open"],
        "registration_bucket": window["registration_bucket"],
        "assigned_draw_date": window["assigned_draw_date"],
        "reveal_at": reveal.isoformat(),
        "seconds_until_reveal": max(int((reveal - now).total_seconds()), 0),
        "reveal_open": now >= reveal and day_index is not None,
    }


async def get_public_event(slug: str, db: AsyncSession) -> dict:
    event = await _event_by_slug(slug, db)
    payload = public_payload(event)
    payload["board"] = await _public_board(event, db)
    draw = await _draw_for(event.id, payload["today"], db)
    payload["drawn"] = draw is not None
    payload["today_count"] = len(await _day_pool(event.id, payload["today"], db))
    if draw and draw.winner_entry_id and payload["reveal_open"]:
        winner = await db.get(EventLuckyEntry, draw.winner_entry_id)
        payload["winner"] = _public_card(winner) if winner else None
    else:
        payload["winner"] = None
    return payload


async def public_live(slug: str, db: AsyncSession) -> dict:
    event = await _event_by_slug(slug, db)
    try:
        raw = await (await _stage_redis()).get(_stage_key(event.id))
    except Exception as exc:
        logger.warning("Lucky stage read failed: %s", exc)
        return {"status": "closed"}
    if not raw:
        return {"status": "closed"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "closed"}


async def publish_stage(announcement_id: str, action: str, db: AsyncSession) -> dict:
    event = await db.get(SiteAnnouncement, announcement_id)
    if not event or not event.lucky_draw_enabled:
        raise HTTPException(status_code=404, detail="Lucky draw event not found")
    client = await _stage_redis()
    key = _stage_key(event.id)
    if action == "close":
        await client.delete(key)
        payload = {"status": "closed", "slug": event.lucky_draw_slug, "session": None}
        await client.publish(LUCKY_STAGE_CHANNEL, json.dumps(payload))
        return payload
    day = ist_today()
    existing_raw = await client.get(key)
    existing = {}
    if existing_raw:
        try:
            existing = json.loads(existing_raw)
        except json.JSONDecodeError:
            existing = {}
    spin_result = None
    if action == "spin":
        spin_result = await admin_reveal(announcement_id, db)
    payload = await _stage_payload(event, day, "spinning" if action == "spin" else "open", db)
    payload["slug"] = event.lucky_draw_slug
    payload["session"] = existing.get("session") or str(uuid.uuid4())
    await client.set(key, json.dumps(payload), ex=1800)
    await client.publish(LUCKY_STAGE_CHANNEL, json.dumps(payload))
    if spin_result:
        return {**spin_result, "stage": payload}
    return payload


async def register(slug: str, body, db: AsyncSession) -> dict:
    event = await _event_by_slug(slug, db, require_open=True)
    window = registration_window(event)
    if not window["registration_open"] or not window["assigned_draw_date"]:
        raise HTTPException(status_code=400, detail="Registration for this event is closed.")
    draw_day = window["assigned_draw_date"]
    eligible = bool(window["draw_eligible"])
    email = body.email.strip().lower()
    phone = re.sub(r"\D", "", body.phone or "")
    if not 10 <= len(phone) <= 12:
        raise HTTPException(status_code=400, detail="Enter a valid 10–12 digit phone number")
    org = (body.organization or "").strip()
    if len(org) < 2:
        raise HTTPException(status_code=400, detail="College / school name is required")
    if body.track not in {"tech", "non_tech"}:
        raise HTTPException(status_code=400, detail="Select Tech or Non-tech")
    photo_url = _save_profile_photo(body.photo)
    phone_key = phone[-10:] if len(phone) >= 10 else phone

    # One verified registration per email for this event (existing platform users still allowed)
    existing_email = await db.execute(
        select(EventLuckyEntry).where(
            EventLuckyEntry.announcement_id == event.id,
            EventLuckyEntry.email == email,
            EventLuckyEntry.email_verified.is_(True),
        )
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This email is already registered for this event")

    # One verified registration per phone for this event
    existing_phone = await db.execute(
        select(EventLuckyEntry).where(
            EventLuckyEntry.announcement_id == event.id,
            EventLuckyEntry.email_verified.is_(True),
            func.right(EventLuckyEntry.phone, 10) == phone_key,
        )
    )
    if existing_phone.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This phone number is already registered for this event")

    pending_result = await db.execute(
        select(EventLuckyEntry).where(
            EventLuckyEntry.announcement_id == event.id,
            EventLuckyEntry.email == email,
            EventLuckyEntry.draw_date == draw_day,
            EventLuckyEntry.email_verified.is_(False),
        )
    )
    entry = pending_result.scalar_one_or_none()
    if entry is None:
        entry = EventLuckyEntry(
            announcement_id=event.id,
            full_name=body.full_name.strip(),
            email=email,
            phone=phone,
            location=(body.location or "").strip()[:250] or None,
            role="seeker",
            organization=org,
            track=body.track,
            photo_url=photo_url,
            draw_eligible=eligible,
            draw_date=draw_day,
        )
        db.add(entry)
    else:
        entry.full_name = body.full_name.strip()
        entry.phone = phone
        entry.location = (body.location or "").strip()[:250] or None
        entry.role = "seeker"
        entry.organization = org
        entry.track = body.track
        entry.photo_url = photo_url
        entry.draw_eligible = eligible
        entry.draw_date = draw_day
    await db.commit()
    await db.refresh(entry)
    code = generate_otp()
    await store_otp(_otp_key(entry.id), code, purpose=OTP_PURPOSE)
    send_otp_email_task.delay(email, code, entry.full_name.split(" ")[0])
    return {"pending_id": entry.id, "email_hint": _hint(email), "message": "We sent a verification code to your email."}


async def verify(slug: str, pending_id: str, otp: str, db: AsyncSession) -> dict:
    event = await _event_by_slug(slug, db)
    entry = await _pending(event.id, pending_id, db)
    if entry.email_verified and entry.ticket_number:
        return _ticket_payload(event, entry)
    ok = await verify_and_consume_otp(_otp_key(entry.id), otp.strip(), purpose=OTP_PURPOSE)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    entry.email_verified = True
    entry.verified_at = datetime.utcnow()
    entry.ticket_number = await _unique_ticket(db)
    track_label = "Tech" if entry.track == "tech" else "Non-tech"
    enquiry = CareerEnquiry(
        full_name=entry.full_name,
        email=entry.email,
        phone=entry.phone,
        qualification=f"{track_label} · {entry.organization}"[:100],
        domain=(event.title or "Lucky draw event")[:150],
        event_title=(event.title or "Lucky draw event")[:200],
        ticket_number=entry.ticket_number,
        announcement_id=event.id,
        draw_date=entry.draw_date,
        location=(entry.location or "")[:200] or None,
        message=(
            f"Lucky draw registration\nEvent: {event.title}\nTicket: {entry.ticket_number}\n"
            f"Day: {entry.draw_date}\nLocation: {entry.location or '-'}\nOrganisation: {entry.organization}\n"
            f"Track: {track_label}"
        ),
        status=DEFAULT_STATUS,
        consent_to_contact=True,
    )
    db.add(enquiry)
    await db.flush()
    entry.enquiry_id = enquiry.id
    credentials = await _ensure_account(entry, db)
    await db.commit()
    await db.refresh(entry)
    if credentials:
        password, first_name, role = credentials
        try:
            await send_password_email(entry.email, first_name, password, role)
        except Exception as exc:
            logger.warning("Lucky draw account email failed for %s: %s", entry.email, exc)
    return _ticket_payload(event, entry)


async def resend(slug: str, pending_id: str, db: AsyncSession) -> dict:
    event = await _event_by_slug(slug, db)
    entry = await _pending(event.id, pending_id, db)
    code = generate_otp()
    await store_otp(_otp_key(entry.id), code, purpose=OTP_PURPOSE)
    send_otp_email_task.delay(entry.email, code, entry.full_name.split(" ")[0])
    return {"pending_id": entry.id, "email_hint": _hint(entry.email), "message": "A new code was sent."}


async def reveal(slug: str, db: AsyncSession, force: bool = False) -> dict:
    event = await _event_by_slug(slug, db)
    day = ist_today()
    if event_day_index(event, day) is None:
        raise HTTPException(status_code=400, detail="Today is outside this event's lucky draw days")
    if not force and ist_now() < reveal_at(event, day):
        raise HTTPException(status_code=400, detail="The result is not ready yet")
    return await _run_draw(event, day, db)


async def admin_reveal(announcement_id: str, db: AsyncSession) -> dict:
    event = await db.get(SiteAnnouncement, announcement_id)
    if not event or not event.lucky_draw_enabled:
        raise HTTPException(status_code=404, detail="Lucky draw event not found")
    day = ist_today()
    if event_day_index(event, day) is None:
        raise HTTPException(status_code=400, detail="Today is not a lucky draw day for this event")
    if ist_now() < reveal_at(event, day):
        raise HTTPException(status_code=400, detail=f"Draw opens at {event.lucky_draw_reveal_time} IST")
    return await _run_draw(event, day, db)


async def list_entries(announcement_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(EventLuckyEntry)
        .where(EventLuckyEntry.announcement_id == announcement_id, EventLuckyEntry.email_verified.is_(True))
        .order_by(EventLuckyEntry.verified_at.desc())
    )
    return [_entry_dict(row) for row in result.scalars().all()]


async def list_people(role: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(EventLuckyEntry, SiteAnnouncement.title)
        .join(SiteAnnouncement, SiteAnnouncement.id == EventLuckyEntry.announcement_id)
        .where(EventLuckyEntry.role == role, EventLuckyEntry.email_verified.is_(True))
        .order_by(EventLuckyEntry.verified_at.desc())
        .limit(100)
    )
    rows = []
    for entry, title in result.all():
        item = _entry_dict(entry)
        item["event_title"] = title
        rows.append(item)
    return rows


async def winner_for_email(email: str, db: AsyncSession) -> Optional[dict]:
    result = await db.execute(
        select(EventLuckyEntry, SiteAnnouncement.title)
        .join(SiteAnnouncement, SiteAnnouncement.id == EventLuckyEntry.announcement_id)
        .where(EventLuckyEntry.email == email.strip().lower(), EventLuckyEntry.is_winner.is_(True))
        .order_by(EventLuckyEntry.verified_at.desc())
    )
    row = result.first()
    if not row:
        return None
    entry, title = row
    return {"event_title": title, "ticket_number": entry.ticket_number, "draw_date": entry.draw_date, "full_name": entry.full_name}


async def _run_draw(event: SiteAnnouncement, day: str, db: AsyncSession) -> dict:
    existing = await _draw_for(event.id, day, db)
    if existing:
        winner = await db.get(EventLuckyEntry, existing.winner_entry_id) if existing.winner_entry_id else None
        pool = await _day_pool(event.id, day, db)
        return {"already_drawn": True, "winner": _winner_dict(winner) if winner else None, "pool": [_entry_dict(item) for item in pool]}

    pool = await _day_pool(event.id, day, db)
    if not pool:
        raise HTTPException(status_code=400, detail="No verified tickets are in this day's draw")
    winner = secrets.choice(pool)
    winner.is_winner = True
    if winner.enquiry_id:
        enquiry = await db.get(CareerEnquiry, winner.enquiry_id)
        if enquiry:
            enquiry.is_event_winner = True
    draw = EventLuckyDraw(
        announcement_id=event.id,
        draw_date=day,
        winner_entry_id=winner.id,
        revealed_at=datetime.utcnow(),
    )
    db.add(draw)
    await db.commit()
    await db.refresh(winner)
    return {"already_drawn": False, "winner": _winner_dict(winner), "pool": [_entry_dict(item) for item in pool]}


async def _day_pool(announcement_id: str, day: str, db: AsyncSession) -> list[EventLuckyEntry]:
    result = await db.execute(
        select(EventLuckyEntry).where(
            EventLuckyEntry.announcement_id == announcement_id,
            EventLuckyEntry.draw_date == day,
            EventLuckyEntry.email_verified.is_(True),
            EventLuckyEntry.draw_eligible.is_(True),
        )
    )
    return list(result.scalars().all())


async def _draw_for(announcement_id: str, day: str, db: AsyncSession) -> Optional[EventLuckyDraw]:
    result = await db.execute(
        select(EventLuckyDraw).where(EventLuckyDraw.announcement_id == announcement_id, EventLuckyDraw.draw_date == day)
    )
    return result.scalar_one_or_none()


async def _event_by_slug(slug: str, db: AsyncSession, require_open: bool = False) -> SiteAnnouncement:
    result = await db.execute(
        select(SiteAnnouncement).where(
            SiteAnnouncement.lucky_draw_slug == slug,
            SiteAnnouncement.lucky_draw_enabled.is_(True),
        )
    )
    event = result.scalar_one_or_none()
    if not event or (require_open and not event.is_active):
        raise HTTPException(status_code=404, detail="This event registration is not available")
    return event


async def _pending(announcement_id: str, pending_id: str, db: AsyncSession) -> EventLuckyEntry:
    entry = await db.get(EventLuckyEntry, pending_id)
    if not entry or entry.announcement_id != announcement_id:
        raise HTTPException(status_code=404, detail="Registration not found")
    return entry


async def _unique_ticket(db: AsyncSession) -> str:
    result = await db.execute(
        select(EventLuckyEntry.ticket_number).where(EventLuckyEntry.ticket_number.like("KOSH-RJ-%"))
    )
    latest = 0
    for (ticket,) in result.all():
        match = re.fullmatch(r"KOSH-RJ-(\d+)", ticket or "")
        if match:
            latest = max(latest, int(match.group(1)))
    for offset in range(1, 30):
        ticket = f"KOSH-RJ-{latest + offset:03d}"
        found = await db.execute(select(EventLuckyEntry.id).where(EventLuckyEntry.ticket_number == ticket))
        if found.scalar_one_or_none() is None:
            return ticket
    raise HTTPException(status_code=500, detail="Could not allocate a ticket number")


def _ticket_payload(event: SiteAnnouncement, entry: EventLuckyEntry) -> dict:
    base = public_payload(event, entry.draw_date)
    return {
        **base,
        "ticket_number": entry.ticket_number,
        "full_name": entry.full_name,
        "email": entry.email,
        "role": entry.role,
        "organization": entry.organization,
        "location": entry.location,
        "track": entry.track,
        "photo_url": entry.photo_url,
        "draw_eligible": bool(entry.draw_eligible),
        "phone": entry.phone,
        "issued_at": ((entry.verified_at or datetime.utcnow()).isoformat() + "Z"),
        "security_hash": hashlib.sha256(f"{entry.ticket_number}:{entry.email}".encode()).hexdigest()[:10].upper(),
    }


def _entry_dict(entry: EventLuckyEntry) -> dict:
    return {
        "id": entry.id,
        "full_name": entry.full_name,
        "email": entry.email,
        "phone": entry.phone,
        "location": entry.location,
        "role": entry.role,
        "organization": entry.organization,
        "ticket_number": entry.ticket_number,
        "draw_date": entry.draw_date,
        "is_winner": entry.is_winner,
        "photo_url": entry.photo_url,
        "draw_eligible": bool(entry.draw_eligible),
    }


LUCKY_STAGE_CHANNEL = "lucky-draw-stage"


def _stage_key(announcement_id: str) -> str:
    return f"lucky-stage:{announcement_id}"


async def _stage_redis():
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2.0)


def _public_card(entry: Optional[EventLuckyEntry]) -> Optional[dict]:
    if not entry:
        return None
    return {
        "id": entry.id,
        "full_name": entry.full_name,
        "email": "",
        "phone": "",
        "location": entry.location,
        "role": "seeker",
        "organization": entry.organization,
        "ticket_number": entry.ticket_number,
        "draw_date": entry.draw_date,
        "is_winner": bool(entry.is_winner),
        "photo_url": entry.photo_url,
    }


async def _public_board(event: SiteAnnouncement, db: AsyncSession) -> list[dict]:
    starts_on, _ends_on = event_span(event)
    start = datetime.strptime(starts_on, "%Y-%m-%d").date()
    total = max(int(event.lucky_draw_days or 1), 1)
    now = ist_now()
    today = ist_today()
    result = await db.execute(select(EventLuckyDraw).where(EventLuckyDraw.announcement_id == event.id))
    draws = {row.draw_date: row for row in result.scalars().all()}
    cards = []
    for index in range(total):
        date = (start + timedelta(days=index)).isoformat()
        reveal = reveal_at(event, date)
        draw = draws.get(date)
        winner = None
        if draw and draw.winner_entry_id and now >= reveal:
            winner = _public_card(await db.get(EventLuckyEntry, draw.winner_entry_id))
        if winner:
            status = "announced"
        elif date == today:
            status = "today"
        elif date < today:
            status = "passed"
        else:
            status = "upcoming"
        cards.append({
            "index": index,
            "date": date,
            "status": status,
            "seconds_until_reveal": max(int((reveal - now).total_seconds()), 0),
            "winner": winner,
        })
    return cards


async def _stage_payload(event: SiteAnnouncement, day: str, status: str, db: AsyncSession) -> dict:
    pool = [_public_card(item) for item in await _day_pool(event.id, day, db)]
    draw = await _draw_for(event.id, day, db)
    winner = None
    if draw and draw.winner_entry_id:
        winner = _public_card(await db.get(EventLuckyEntry, draw.winner_entry_id))
        if winner:
            winner["is_winner"] = True
    index = event_day_index(event, day)
    return {
        "status": status,
        "event_title": event.title or "Lucky draw",
        "day_number": (index or 0) + 1,
        "total_days": max(int(event.lucky_draw_days or 1), 1),
        "started_at": ist_now().isoformat() if status == "spinning" else None,
        "action": "spin" if status == "spinning" else "open",
        "winner": winner if status == "spinning" else None,
        "pool": [item for item in pool if item],
    }


def _winner_dict(entry: Optional[EventLuckyEntry]) -> Optional[dict]:
    if not entry:
        return None
    data = _entry_dict(entry)
    data["is_winner"] = True
    return data


def _save_profile_photo(raw: str) -> str:
    payload = (raw or "").strip()
    if payload.startswith("data:"):
        header, _, payload = payload.partition(",")
        if "image/" not in header:
            raise HTTPException(status_code=400, detail="Profile photo must be an image")
    try:
        data = base64.b64decode(payload, validate=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Profile photo could not be read") from exc
    if len(data) < 32 or len(data) > 2_500_000:
        raise HTTPException(status_code=400, detail="Profile photo must be under 2.5 MB")
    if data.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        ext = ".webp"
    else:
        raise HTTPException(status_code=400, detail="Use a JPG, PNG, or WEBP profile photo")
    folder = get_upload_dir() / "lucky_profiles"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (folder / name).write_bytes(data)
    return f"/uploads/lucky_profiles/{name}"


def _otp_key(entry_id: str) -> str:
    return f"lucky-{entry_id}@rojgarmela.local"


def _hint(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"
