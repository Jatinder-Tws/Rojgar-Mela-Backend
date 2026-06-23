"""Help desk bot — text chat, escalation, and ticket creation."""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import NotificationType
from models.support_ticket import (
    SupportTicket,
    TicketCategory,
    TicketMessage,
    TicketPriority,
    TicketStatus,
)
from models.user import User
from services.ai_service import get_ai
from services.notification_service import notify_super_admins
from services.support_bot_knowledge import build_system_prompt
from services.support_realtime_service import broadcast_ticket_message, broadcast_ticket_update

logger = logging.getLogger(__name__)

ESCALATE_KEYWORDS = re.compile(
    r"\b(human|agent|person|representative|escalat|ticket|support\s*team|"
    r"baat\s*karo|insaan|madad\s*chahiye|help\s*desk)\b",
    re.IGNORECASE,
)


@dataclass
class BotChatMessage:
    role: str  # user | assistant
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BotSession:
    user_id: str
    user_role: str
    messages: List[BotChatMessage] = field(default_factory=list)
    ticket_id: Optional[str] = None
    escalated: bool = False


# In-memory sessions (per server instance)
_sessions: dict[str, BotSession] = {}


def get_or_create_session(user_id: str, user_role: str) -> BotSession:
    if user_id not in _sessions:
        _sessions[user_id] = BotSession(user_id=user_id, user_role=user_role)
    return _sessions[user_id]


def clear_session(user_id: str) -> None:
    _sessions.pop(user_id, None)


def _parse_bot_response(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {
        "can_answer": True,
        "reply": raw or "I'm sorry, I couldn't process that. Please try again.",
        "should_escalate": False,
        "ticket_subject": None,
        "ticket_category": None,
    }


def _generate_ticket_number() -> str:
    return f"RM-{datetime.utcnow().strftime('%y%m%d')}-{random.randint(1000, 9999)}"


def _user_display_name(user: User) -> str:
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return name or user.email


def _conversation_text(messages: List[BotChatMessage]) -> str:
    lines = []
    for m in messages:
        label = "User" if m.role == "user" else "Bot"
        lines.append(f"{label}: {m.content}")
    return "\n".join(lines)


async def process_text_message(
    user: User,
    text: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Process a text message; returns bot reply payload."""
    user_role = user.role.value if hasattr(user.role, "value") else str(user.role or "seeker")
    session = get_or_create_session(str(user.id), user_role)

    # Reset escalation if the existing ticket is closed or resolved
    if session.escalated and session.ticket_id:
        result = await db.execute(select(SupportTicket).where(SupportTicket.id == session.ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket or ticket.status in (TicketStatus.closed, TicketStatus.resolved):
            session.escalated = False
            session.ticket_id = None

    session.messages.append(BotChatMessage(role="user", content=text.strip()))

    force_escalate = bool(ESCALATE_KEYWORDS.search(text))

    if force_escalate and not session.escalated:
        ticket = await _create_ticket_from_session(user, session, db, subject_prefix="User requested human support")
        session.escalated = True
        session.ticket_id = ticket.id
        reply = "Main aapki support ticket raise kar deta hoon, customer support jald hi aapki problem ko solve karenge."
        session.messages.append(BotChatMessage(role="assistant", content=reply))
        return {
            "type": "bot_text",
            "content": reply,
            "can_answer": False,
            "escalated": True,
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
        }

    history = session.messages[-10:]
    convo = "\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}" for m in history[:-1]
    )
    user_prompt = f"Conversation so far:\n{convo}\n\nUser: {text}\n\nRespond with JSON."

    try:
        ai = get_ai()
        raw = await ai.chat_completion(build_system_prompt(user_role), user_prompt)
        parsed = _parse_bot_response(raw)
    except Exception as exc:
        logger.exception("Bot AI error: %s", exc)
        parsed = {
            "can_answer": False,
            "reply": "I'm having trouble right now. Let me connect you with our support team.",
            "should_escalate": True,
            "ticket_subject": "Bot unavailable — user needs help",
            "ticket_category": "technical",
        }

    reply = (parsed.get("reply") or "").strip()
    options = parsed.get("options")
    should_escalate = bool(parsed.get("should_escalate")) or not parsed.get("can_answer", True)

    if should_escalate and not session.escalated:
        subject = parsed.get("ticket_subject") or f"Help request: {text[:80]}"
        ticket = await _create_ticket_from_session(user, session, db, subject_prefix=subject)
        session.escalated = True
        session.ticket_id = ticket.id
        reply = "Main aapki support ticket raise kar deta hoon, customer support jald hi aapki problem ko solve karenge."
        return {
            "type": "bot_text",
            "content": reply,
            "options": options,
            "can_answer": False,
            "escalated": True,
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
        }

    session.messages.append(BotChatMessage(role="assistant", content=reply))
    return {
        "type": "bot_text",
        "content": reply,
        "options": options,
        "can_answer": True,
        "escalated": False,
        "ticket_id": session.ticket_id,
    }


async def escalate_session(user: User, db: AsyncSession) -> dict[str, Any]:
    user_role = user.role.value if hasattr(user.role, "value") else str(user.role or "seeker")
    session = get_or_create_session(str(user.id), user_role)

    # Reset escalation if the existing ticket is closed or resolved
    if session.escalated and session.ticket_id:
        result = await db.execute(select(SupportTicket).where(SupportTicket.id == session.ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket or ticket.status in (TicketStatus.closed, TicketStatus.resolved):
            session.escalated = False
            session.ticket_id = None
        else:
            return {
                "type": "ticket_created",
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "content": f"Ticket [{ticket.ticket_number}] is already open.",
            }

    ticket = await _create_ticket_from_session(
        user, session, db, subject_prefix="Escalated from AI Help Assistant"
    )
    session.escalated = True
    session.ticket_id = ticket.id
    msg = "Main aapki support ticket raise kar deta hoon, customer support jald hi aapki problem ko solve karenge."
    session.messages.append(BotChatMessage(role="assistant", content=msg))
    return {
        "type": "ticket_created",
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "content": msg,
    }


async def _create_ticket_from_session(
    user: User,
    session: BotSession,
    db: AsyncSession,
    subject_prefix: str = "Help Desk Bot Escalation",
) -> SupportTicket:
    convo = _conversation_text(session.messages)
    description = convo if convo else "User requested support via AI Help Assistant."

    ticket_number = _generate_ticket_number()
    for _ in range(5):
        exists = await db.execute(select(SupportTicket).where(SupportTicket.ticket_number == ticket_number))
        if not exists.scalar_one_or_none():
            break
        ticket_number = _generate_ticket_number()

    ticket = SupportTicket(
        user_id=user.id,
        ticket_number=ticket_number,
        category=TicketCategory.other,
        subject=subject_prefix[:200],
        description=description[:5000],
        priority=TicketPriority.medium,
        status=TicketStatus.open,
        bot_handled=True,
        escalated_at=datetime.utcnow(),
    )
    db.add(ticket)
    await db.flush()

    initial_msg = TicketMessage(
        ticket_id=ticket.id,
        author_id=user.id,
        body=description[:5000],
        is_staff_reply=False,
        is_bot_reply=False,
    )
    db.add(initial_msg)

    bot_summary = TicketMessage(
        ticket_id=ticket.id,
        author_id=None,
        body="[AI Assistant] Conversation escalated to human support. Please review the transcript above.",
        is_staff_reply=False,
        is_bot_reply=True,
    )
    db.add(bot_summary)
    await db.commit()
    await db.refresh(ticket)

    role_label = "Job Seeker" if session.user_role == "seeker" else "Provider"
    await notify_super_admins(
        db,
        title="Help Desk Bot Escalation",
        message=f"[{ticket.ticket_number}] {role_label} {_user_display_name(user)}: {ticket.subject}",
        type=NotificationType.general,
        related_user_id=str(user.id),
    )

    from controllers.support_controller import _message_to_out

    initial_out = _message_to_out(initial_msg, user)
    await broadcast_ticket_message(db, ticket, initial_out)
    await broadcast_ticket_update(db, ticket, action="escalated")

    return ticket
