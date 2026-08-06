from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer


def _utc_iso(dt: datetime) -> str:
    """Always emit UTC ISO string with Z suffix so browsers parse correctly."""
    if dt is None:
        return ''
    return dt.isoformat() + 'Z'


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
    is_bot_reply: bool = False
    created_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return _utc_iso(value)

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

    @field_serializer('created_at', 'updated_at')
    def serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value)

    @field_serializer('resolved_at', 'last_message_at')
    def serialize_optional_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_iso(value) if value else None

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

    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    items: List[FeedbackOut]
    total: int


class InquiryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    subject: Optional[str] = Field(None, max_length=200)
    message: str = Field(..., min_length=5, max_length=5000)


class InquiryOut(BaseModel):
    id: str
    name: str
    email: str
    subject: Optional[str] = None
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class InquiryListResponse(BaseModel):
    items: List[InquiryOut]
    total: int


class InquiryReplyCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)


