from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.super_admin.controllers.support_controller import (
    add_user_message as ctrl_add_message,
    create_ticket as ctrl_create_ticket,
    delete_my_ticket as ctrl_delete_ticket,
    delete_user_message as ctrl_delete_message,
    get_my_ticket as ctrl_get_ticket,
    list_my_feedback as ctrl_list_my_feedback,
    list_my_tickets as ctrl_list_tickets,
    submit_feedback as ctrl_submit_feedback,
    create_contact_inquiry as ctrl_create_inquiry,
    update_my_ticket as ctrl_update_ticket,
    update_user_message as ctrl_update_message,
)
from app.core.database import get_db
from app.shared.models.user import User
from app.modules.super_admin.schemas.support import (
    FeedbackCreate,
    FeedbackOut,
    TicketCreate,
    TicketDetailOut,
    TicketMessageCreate,
    TicketMessageOut,
    TicketOut,
    TicketUpdate,
    InquiryCreate,
    InquiryOut,
)
from app.core.dependencies import require_seeker_or_provider

router = APIRouter(prefix="/support", tags=["support"])


@router.post("/tickets", response_model=TicketDetailOut, status_code=201)
async def create_ticket(
    body: TicketCreate,
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_create_ticket(body, user, db)


@router.get("/tickets", response_model=List[TicketOut])
async def list_tickets(
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_list_tickets(user, db)


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket(
    ticket_id: str,
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_get_ticket(ticket_id, user, db)


@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessageOut)
async def reply_to_ticket(
    ticket_id: str,
    body: TicketMessageCreate,
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_add_message(ticket_id, body, user, db)


@router.patch("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def update_ticket(
    ticket_id: str,
    body: TicketUpdate,
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_update_ticket(ticket_id, body, user, db)


@router.delete("/tickets/{ticket_id}", status_code=204)
async def delete_ticket(
    ticket_id: str,
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    await ctrl_delete_ticket(ticket_id, user, db)


@router.patch("/tickets/{ticket_id}/messages/{message_id}", response_model=TicketMessageOut)
async def edit_ticket_message(
    ticket_id: str,
    message_id: str,
    body: TicketMessageCreate,
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_update_message(ticket_id, message_id, body, user, db)


@router.delete("/tickets/{ticket_id}/messages/{message_id}", status_code=204)
async def delete_ticket_message(
    ticket_id: str,
    message_id: str,
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    await ctrl_delete_message(ticket_id, message_id, user, db)


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    body: FeedbackCreate,
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_submit_feedback(body, user, db)


@router.get("/feedback", response_model=List[FeedbackOut])
async def list_my_feedback(
    user: User = Depends(require_seeker_or_provider),
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_list_my_feedback(user, db)


@router.post("/inquiries", response_model=InquiryOut, status_code=201)
async def create_inquiry(
    body: InquiryCreate,
    db: AsyncSession = Depends(get_db),
):
    return await ctrl_create_inquiry(body, db)
