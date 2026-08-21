import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.shared.models.user import User
from app.modules.super_admin.schemas.support import TicketMessageOut

logger = logging.getLogger(__name__)


async def _publish_to_user(user_id: str, payload: dict) -> None:
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.publish(f"user_events:{user_id}", json.dumps(payload))
        await r.aclose()
    except Exception as e:
        logger.warning(f"Failed to publish ticket event for user {user_id}: {e}")


def _serialize_message(msg: TicketMessageOut) -> dict[str, Any]:
    data = msg.model_dump()
    created = data.get("created_at")
    if isinstance(created, datetime):
        data["created_at"] = created.isoformat()
    return data


async def _broadcast_to_super_admins(db: AsyncSession, payload: dict) -> None:
    result = await db.execute(select(User.id).where(User.is_super_admin.is_(True)))
    for admin_id in result.scalars().all():
        await _publish_to_user(str(admin_id), payload)


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
    await _publish_to_user(str(ticket.user_id), payload)
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
    await _publish_to_user(str(ticket.user_id), payload)
    await _broadcast_to_super_admins(db, payload)
