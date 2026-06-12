from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    category: str = "other"
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    priority: str = "medium"


class TicketMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class TicketMessageOut(BaseModel):
    id: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    body: str
    is_staff_reply: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TicketOut(BaseModel):
    id: str
    ticket_number: str
    category: str
    subject: str
    description: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None

    class Config:
        from_attributes = True


class TicketDetailOut(TicketOut):
    messages: List[TicketMessageOut] = []


class TicketListResponse(BaseModel):
    items: List[TicketOut]
    total: int


class TicketStatusUpdate(BaseModel):
    status: str


class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    category: str = "general"
    comment: str = Field(..., min_length=5, max_length=2000)
    page_context: Optional[str] = None


class FeedbackOut(BaseModel):
    id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    rating: int
    category: str
    comment: str
    page_context: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    items: List[FeedbackOut]
    total: int
