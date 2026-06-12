from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.support_controller import (
    admin_get_ticket as ctrl_get_ticket,
    admin_list_feedback as ctrl_list_feedback,
    admin_list_tickets as ctrl_list_tickets,
    admin_reply_ticket as ctrl_reply,
    admin_update_ticket_status as ctrl_update_status,
)
from database import get_db
from models.user import User
from schemas.support import (
    FeedbackListResponse,
    TicketDetailOut,
    TicketListResponse,
    TicketMessageCreate,
    TicketMessageOut,
    TicketOut,
    TicketStatusUpdate,
)
from services.auth_service import require_super_admin

router = APIRouter(prefix="/super-admin/support", tags=["super-admin-support"])


@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_list_tickets(db, page=page, page_size=page_size, search=search, status=status)


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket(
    ticket_id: str,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_ticket(ticket_id, db)


@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessageOut)
async def reply_to_ticket(
    ticket_id: str,
    body: TicketMessageCreate,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_reply(ticket_id, body, admin, db)


@router.patch("/tickets/{ticket_id}/status", response_model=TicketOut)
async def update_ticket_status(
    ticket_id: str,
    body: TicketStatusUpdate,
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_update_status(ticket_id, body, db)


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    rating: Optional[int] = Query(None, ge=1, le=5),
    _admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_list_feedback(db, page=page, page_size=page_size, search=search, rating=rating)
