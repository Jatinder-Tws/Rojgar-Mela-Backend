import logging
import random
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.notification import NotificationType
from models.platform_feedback import FeedbackCategory, PlatformFeedback
from models.support_ticket import (
    SupportTicket,
    TicketCategory,
    TicketMessage,
    TicketPriority,
    TicketStatus,
)
from models.contact_inquiry import ContactInquiry
from models.user import User
from schemas.support import (
    FeedbackCreate,
    FeedbackListResponse,
    FeedbackOut,
    TicketCreate,
    TicketDetailOut,
    TicketListResponse,
    TicketMessageCreate,
    TicketMessageOut,
    TicketOut,
    TicketStatusUpdate,
    InquiryCreate,
    InquiryOut,
    InquiryListResponse,
    InquiryReplyCreate,
)
from services.notification_service import create_notification, notify_super_admins
from services.support_realtime_service import broadcast_ticket_message, broadcast_ticket_update

logger = logging.getLogger(__name__)


async def _safe_notify_user(db: AsyncSession, user_id: str, title: str, message: str, related_user_id: Optional[str] = None):
    try:
        await create_notification(
            db,
            user_id=user_id,
            type=NotificationType.general,
            title=title,
            message=message,
            related_user_id=related_user_id,
            email_notification=False,
        )
    except Exception as exc:
        logger.warning("Support notification failed (non-fatal): %s", exc)


async def _safe_broadcast_message(db: AsyncSession, ticket, msg_out: TicketMessageOut):
    try:
        await broadcast_ticket_message(db, ticket, msg_out)
    except Exception as exc:
        logger.warning("Support websocket broadcast failed (non-fatal): %s", exc)


def _user_role_str(user: User) -> str:
    if getattr(user, "is_super_admin", False):
        return "super_admin"
    if user.role is None:
        return "user"
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def _user_display_name(user: User) -> str:
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return name or user.email


def _generate_ticket_number() -> str:
    return f"RM-{datetime.utcnow().strftime('%y%m%d')}-{random.randint(1000, 9999)}"


def _ticket_to_out(
    ticket: SupportTicket,
    message_count: int = 0,
    last_message_at: Optional[datetime] = None,
    ticket_user: Optional[User] = None,
) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        category=ticket.category.value if hasattr(ticket.category, "value") else str(ticket.category),
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
        priority=ticket.priority.value if hasattr(ticket.priority, "value") else str(ticket.priority),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        message_count=message_count,
        last_message_at=last_message_at,
        user_name=_user_display_name(ticket_user) if ticket_user else None,
        user_email=ticket_user.email if ticket_user else None,
        user_role=_user_role_str(ticket_user) if ticket_user else None,
    )


def _message_to_out(msg: TicketMessage, author: Optional[User] = None) -> TicketMessageOut:
    if msg.is_bot_reply:
        author_name = "AI Assistant"
        author_role = "bot"
    elif msg.is_staff_reply:
        author_name = "Support Team"
        author_role = "super_admin"
    elif author:
        author_name = _user_display_name(author)
        author_role = _user_role_str(author)
    else:
        author_name = None
        author_role = None

    return TicketMessageOut(
        id=msg.id,
        author_id=msg.author_id,
        author_name=author_name,
        author_role=author_role,
        body=msg.body,
        is_staff_reply=msg.is_staff_reply,
        is_bot_reply=bool(getattr(msg, "is_bot_reply", False)),
        created_at=msg.created_at,
    )


async def _get_user_ticket(ticket_id: str, user: User, db: AsyncSession) -> SupportTicket:
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id, SupportTicket.user_id == user.id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


async def _get_ticket_admin(ticket_id: str, db: AsyncSession) -> SupportTicket:
    result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


# ── User: Tickets ────────────────────────────────────────────────────────────

async def create_ticket(body: TicketCreate, user: User, db: AsyncSession) -> TicketDetailOut:
    try:
        category = TicketCategory(body.category)
    except ValueError:
        category = TicketCategory.other
    try:
        priority = TicketPriority(body.priority)
    except ValueError:
        priority = TicketPriority.medium

    ticket_number = _generate_ticket_number()
    for _ in range(5):
        exists = await db.execute(select(SupportTicket).where(SupportTicket.ticket_number == ticket_number))
        if not exists.scalar_one_or_none():
            break
        ticket_number = _generate_ticket_number()

    ticket = SupportTicket(
        user_id=user.id,
        ticket_number=ticket_number,
        category=category,
        subject=body.subject.strip(),
        description=body.description.strip(),
        priority=priority,
        status=TicketStatus.open,
    )
    db.add(ticket)
    await db.flush()

    initial_msg = TicketMessage(
        ticket_id=ticket.id,
        author_id=user.id,
        body=body.description.strip(),
        is_staff_reply=False,
    )
    db.add(initial_msg)
    await db.commit()
    await db.refresh(ticket)

    role_label = "Job Seeker" if _user_role_str(user) == "seeker" else "Provider"
    await notify_super_admins(
        db,
        title="New Support Ticket",
        message=f"[{ticket.ticket_number}] {role_label} {_user_display_name(user)}: {ticket.subject}",
        type=NotificationType.general,
        related_user_id=str(user.id),
    )

    initial_out = _message_to_out(initial_msg, user)
    await broadcast_ticket_message(db, ticket, initial_out)
    await broadcast_ticket_update(db, ticket, action="created")

    return TicketDetailOut(
        **_ticket_to_out(ticket, message_count=1, last_message_at=initial_msg.created_at).model_dump(),
        messages=[initial_out],
    )


async def list_my_tickets(user: User, db: AsyncSession) -> List[TicketOut]:
    msg_count_sq = (
        select(func.count(TicketMessage.id))
        .where(TicketMessage.ticket_id == SupportTicket.id)
        .correlate(SupportTicket)
        .scalar_subquery()
    )
    last_msg_sq = (
        select(func.max(TicketMessage.created_at))
        .where(TicketMessage.ticket_id == SupportTicket.id)
        .correlate(SupportTicket)
        .scalar_subquery()
    )

    result = await db.execute(
        select(SupportTicket, msg_count_sq, last_msg_sq)
        .where(SupportTicket.user_id == user.id)
        .order_by(SupportTicket.updated_at.desc())
        .limit(100)
    )
    rows = result.all()
    return [_ticket_to_out(t, int(mc or 0), lm) for t, mc, lm in rows]


async def get_my_ticket(ticket_id: str, user: User, db: AsyncSession) -> TicketDetailOut:
    result = await db.execute(
        select(SupportTicket)
        .options(selectinload(SupportTicket.messages))
        .where(SupportTicket.id == ticket_id, SupportTicket.user_id == user.id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    author_ids = {m.author_id for m in ticket.messages if m.author_id}
    authors_map: dict[str, User] = {}
    if author_ids:
        authors_result = await db.execute(select(User).where(User.id.in_(author_ids)))
        authors_map = {u.id: u for u in authors_result.scalars().all()}

    messages = [
        _message_to_out(m, authors_map.get(m.author_id) if m.author_id else None)
        for m in ticket.messages
    ]
    last_at = messages[-1].created_at if messages else None
    return TicketDetailOut(
        **_ticket_to_out(ticket, message_count=len(messages), last_message_at=last_at).model_dump(),
        messages=messages,
    )


async def add_user_message(ticket_id: str, body: TicketMessageCreate, user: User, db: AsyncSession) -> TicketMessageOut:
    ticket = await _get_user_ticket(ticket_id, user, db)
    if ticket.status in (TicketStatus.resolved, TicketStatus.closed):
        raise HTTPException(status_code=400, detail="This ticket is closed. Please open a new ticket.")

    msg = TicketMessage(
        ticket_id=ticket.id,
        author_id=user.id,
        body=body.body.strip(),
        is_staff_reply=False,
    )
    db.add(msg)
    ticket.updated_at = datetime.utcnow()
    if ticket.status == TicketStatus.resolved:
        ticket.status = TicketStatus.open
    await db.commit()
    await db.refresh(msg)

    await notify_super_admins(
        db,
        title="Ticket Reply",
        message=f"[{ticket.ticket_number}] New reply from {_user_display_name(user)}",
        type=NotificationType.general,
        related_user_id=str(user.id),
    )

    msg_out = _message_to_out(msg, user)
    await _safe_broadcast_message(db, ticket, msg_out)
    return msg_out


# ── User: Feedback ───────────────────────────────────────────────────────────

async def submit_feedback(body: FeedbackCreate, user: User, db: AsyncSession) -> FeedbackOut:
    try:
        category = FeedbackCategory(body.category)
    except ValueError:
        category = FeedbackCategory.general

    fb = PlatformFeedback(
        user_id=user.id,
        rating=body.rating,
        category=category,
        comment=body.comment.strip(),
        page_context=body.page_context,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    role_label = "Job Seeker" if _user_role_str(user) == "seeker" else "Provider"
    await notify_super_admins(
        db,
        title="New Platform Feedback",
        message=f"{role_label} {_user_display_name(user)} rated {body.rating}/5",
        type=NotificationType.general,
        related_user_id=str(user.id),
    )

    return FeedbackOut(
        id=fb.id,
        user_id=fb.user_id,
        user_name=_user_display_name(user),
        user_email=user.email,
        user_role=_user_role_str(user),
        rating=fb.rating,
        category=fb.category.value,
        comment=fb.comment,
        page_context=fb.page_context,
        created_at=fb.created_at,
    )


async def list_my_feedback(user: User, db: AsyncSession) -> List[FeedbackOut]:
    result = await db.execute(
        select(PlatformFeedback)
        .where(PlatformFeedback.user_id == user.id)
        .order_by(PlatformFeedback.created_at.desc())
        .limit(50)
    )
    items = result.scalars().all()
    return [
        FeedbackOut(
            id=fb.id,
            user_id=fb.user_id,
            user_name=_user_display_name(user),
            user_email=user.email,
            user_role=_user_role_str(user),
            rating=fb.rating,
            category=fb.category.value if hasattr(fb.category, "value") else str(fb.category),
            comment=fb.comment,
            page_context=fb.page_context,
            created_at=fb.created_at,
        )
        for fb in items
    ]


# ── Admin: Tickets ───────────────────────────────────────────────────────────

async def admin_list_tickets(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> TicketListResponse:
    query = select(SupportTicket, User).join(User, SupportTicket.user_id == User.id)
    count_query = select(func.count()).select_from(SupportTicket)

    if status and status != "all":
        try:
            status_enum = TicketStatus(status)
            query = query.where(SupportTicket.status == status_enum)
            count_query = count_query.where(SupportTicket.status == status_enum)
        except ValueError:
            pass

    if search:
        term = f"%{search.strip()}%"
        filt = or_(
            SupportTicket.subject.ilike(term),
            SupportTicket.ticket_number.ilike(term),
            SupportTicket.description.ilike(term),
        )
        query = query.where(filt)
        count_query = count_query.where(filt)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(SupportTicket.updated_at.desc()).offset(offset).limit(page_size)
    )
    rows = result.all()

    items: List[TicketOut] = []
    for ticket, ticket_user in rows:
        mc_result = await db.execute(
            select(func.count()).where(TicketMessage.ticket_id == ticket.id)
        )
        lm_result = await db.execute(
            select(func.max(TicketMessage.created_at)).where(TicketMessage.ticket_id == ticket.id)
        )
        items.append(
            _ticket_to_out(
                ticket,
                message_count=mc_result.scalar() or 0,
                last_message_at=lm_result.scalar(),
                ticket_user=ticket_user,
            )
        )

    return TicketListResponse(items=items, total=total)


async def admin_get_ticket(ticket_id: str, db: AsyncSession) -> TicketDetailOut:
    result = await db.execute(
        select(SupportTicket)
        .options(selectinload(SupportTicket.messages), selectinload(SupportTicket.user))
        .where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    author_ids = {m.author_id for m in ticket.messages if m.author_id}
    authors_map: dict[str, User] = {}
    if author_ids:
        authors_result = await db.execute(select(User).where(User.id.in_(author_ids)))
        authors_map = {u.id: u for u in authors_result.scalars().all()}

    messages = [
        _message_to_out(m, authors_map.get(m.author_id) if m.author_id else None)
        for m in ticket.messages
    ]
    last_at = messages[-1].created_at if messages else None
    return TicketDetailOut(
        **_ticket_to_out(
            ticket,
            message_count=len(messages),
            last_message_at=last_at,
            ticket_user=ticket.user,
        ).model_dump(),
        messages=messages,
    )


async def admin_reply_ticket(
    ticket_id: str,
    body: TicketMessageCreate,
    admin: User,
    db: AsyncSession,
) -> TicketMessageOut:
    ticket = await _get_ticket_admin(ticket_id, db)

    msg = TicketMessage(
        ticket_id=ticket.id,
        author_id=admin.id,
        body=body.body.strip(),
        is_staff_reply=True,
    )
    db.add(msg)
    ticket.updated_at = datetime.utcnow()
    if ticket.status == TicketStatus.open:
        ticket.status = TicketStatus.in_progress
    await db.commit()
    await db.refresh(msg)

    msg_out = _message_to_out(msg, admin)
    await _safe_notify_user(
        db,
        user_id=str(ticket.user_id),
        title="Support Team Replied",
        message=f"Your ticket [{ticket.ticket_number}] has a new reply from Rojgar Mela Support.",
        related_user_id=str(admin.id),
    )
    await _safe_broadcast_message(db, ticket, msg_out)
    return msg_out


async def admin_update_ticket_status(
    ticket_id: str,
    body: TicketStatusUpdate,
    db: AsyncSession,
) -> TicketOut:
    ticket = await _get_ticket_admin(ticket_id, db)
    try:
        new_status = TicketStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    if new_status in (TicketStatus.resolved, TicketStatus.closed):
        ticket.resolved_at = datetime.utcnow()
    else:
        ticket.resolved_at = None

    await db.commit()
    await db.refresh(ticket)

    status_label = new_status.value.replace("_", " ").title()
    await create_notification(
        db,
        user_id=str(ticket.user_id),
        type=NotificationType.general,
        title=f"Ticket {status_label}",
        message=f"Your support ticket [{ticket.ticket_number}] is now {status_label.lower()}.",
        email_notification=False,
    )

    await broadcast_ticket_update(db, ticket, action="status_changed")

    mc_result = await db.execute(select(func.count()).where(TicketMessage.ticket_id == ticket.id))
    lm_result = await db.execute(
        select(func.max(TicketMessage.created_at)).where(TicketMessage.ticket_id == ticket.id)
    )
    return _ticket_to_out(
        ticket,
        message_count=mc_result.scalar() or 0,
        last_message_at=lm_result.scalar(),
    )


# ── Admin: Feedback ──────────────────────────────────────────────────────────

async def admin_list_feedback(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    rating: Optional[int] = None,
) -> FeedbackListResponse:
    query = (
        select(PlatformFeedback, User)
        .join(User, PlatformFeedback.user_id == User.id)
    )
    count_query = select(func.count()).select_from(PlatformFeedback).join(
        User, PlatformFeedback.user_id == User.id
    )

    if rating:
        query = query.where(PlatformFeedback.rating == rating)
        count_query = count_query.where(PlatformFeedback.rating == rating)

    if search:
        term = f"%{search.strip()}%"
        filt = or_(
            PlatformFeedback.comment.ilike(term),
            User.email.ilike(term),
            User.first_name.ilike(term),
            User.last_name.ilike(term),
        )
        query = query.where(filt)
        count_query = count_query.where(filt)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(PlatformFeedback.created_at.desc()).offset(offset).limit(page_size)
    )
    rows = result.all()

    items = [
        FeedbackOut(
            id=fb.id,
            user_id=fb.user_id,
            user_name=_user_display_name(u),
            user_email=u.email,
            user_role=_user_role_str(u),
            rating=fb.rating,
            category=fb.category.value if hasattr(fb.category, "value") else str(fb.category),
            comment=fb.comment,
            page_context=fb.page_context,
            created_at=fb.created_at,
        )
        for fb, u in rows
    ]
    return FeedbackListResponse(items=items, total=total)


async def create_contact_inquiry(body: InquiryCreate, db: AsyncSession) -> InquiryOut:
    inquiry = ContactInquiry(
        name=body.name.strip(),
        email=body.email.strip(),
        subject=body.subject.strip() if body.subject else None,
        message=body.message.strip(),
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)

    # Notify super admins of the new contact inquiry
    await notify_super_admins(
        db=db,
        title="New Contact Inquiry",
        message=f"New inquiry from {inquiry.name} ({inquiry.email}): {inquiry.subject or '(No Subject)'}",
        type=NotificationType.general,
        related_user_id=str(inquiry.id),
    )

    return InquiryOut(
        id=inquiry.id,
        name=inquiry.name,
        email=inquiry.email,
        subject=inquiry.subject,
        message=inquiry.message,
        created_at=inquiry.created_at,
    )


async def admin_list_inquiries(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> InquiryListResponse:
    query = select(ContactInquiry)
    count_query = select(func.count()).select_from(ContactInquiry)

    if search:
        term = f"%{search.strip()}%"
        filt = or_(
            ContactInquiry.name.ilike(term),
            ContactInquiry.email.ilike(term),
            ContactInquiry.subject.ilike(term),
            ContactInquiry.message.ilike(term),
        )
        query = query.where(filt)
        count_query = count_query.where(filt)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(ContactInquiry.created_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return InquiryListResponse(
        items=[
            InquiryOut(
                id=item.id,
                name=item.name,
                email=item.email,
                subject=item.subject,
                message=item.message,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
    )


async def admin_reply_to_inquiry(
    inquiry_id: str,
    body: InquiryReplyCreate,
    db: AsyncSession,
) -> dict:
    result = await db.execute(select(ContactInquiry).where(ContactInquiry.id == inquiry_id))
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    from services.celery_tasks import send_inquiry_reply_email
    send_inquiry_reply_email.delay(
        to_email=inquiry.email,
        subject=body.subject.strip(),
        message_body=body.message.strip(),
    )
    return {"message": "Email reply enqueued successfully"}

