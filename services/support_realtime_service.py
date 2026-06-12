from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.support import TicketMessageOut
from services.websocket_manager import manager


def _serialize_message(msg: TicketMessageOut) -> dict[str, Any]:
    data = msg.model_dump()
    created = data.get("created_at")
    if isinstance(created, datetime):
        data["created_at"] = created.isoformat()
    return data


async def _broadcast_to_super_admins(db: AsyncSession, payload: dict) -> None:
    result = await db.execute(select(User).where(User.is_super_admin.is_(True)))
    for admin in result.scalars().all():
        await manager.send_personal_message(payload, str(admin.id))


async def broadcast_ticket_message(db: AsyncSession, ticket, msg_out: TicketMessageOut) -> None:
    status = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
    payload = {
        "type": "TICKET_MESSAGE",
        "data": {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "status": status,
            "message": _serialize_message(msg_out),
        },
    }
    await manager.send_personal_message(payload, str(ticket.user_id))
    await _broadcast_to_super_admins(db, payload)


async def broadcast_ticket_update(db: AsyncSession, ticket, action: str = "updated") -> None:
    status = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
    updated = ticket.updated_at.isoformat() if ticket.updated_at else None
    payload = {
        "type": "TICKET_UPDATE",
        "data": {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "status": status,
            "action": action,
            "updated_at": updated,
        },
    }
    await manager.send_personal_message(payload, str(ticket.user_id))
    await _broadcast_to_super_admins(db, payload)
