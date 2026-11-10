from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator


def _utc_iso(dt: datetime) -> str:
    """Always emit UTC ISO string with Z suffix so browsers parse correctly."""
    if dt is None:
        return ''
    if dt.tzinfo is not None:
        # Avoid ...+00:00Z which is invalid in JS Date parsers
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat() + 'Z'


class TicketCreate(BaseModel):
    category: str = "other"
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    priority: str = "medium"
    source: str = "job_portal"

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        normalized = (value or "job_portal").strip().lower()
        if normalized not in {"job_portal", "training"}:
            raise ValueError("source must be job_portal or training")
        return normalized


class TicketMessageCreate(BaseModel):
    body: str = Field(default="", max_length=5000)
    attachment_url: Optional[str] = Field(default=None, max_length=500)
    attachment_filename: Optional[str] = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_body_or_attachment(self):
        text = (self.body or "").strip()
        url = (self.attachment_url or "").strip()
        if not text and not url:
            raise ValueError("Message text or attachment is required")
        if url and not url.startswith("/uploads/"):
            raise ValueError("Invalid attachment URL")
        self.body = text
        self.attachment_url = url or None
        if self.attachment_filename:
            self.attachment_filename = self.attachment_filename.strip()[:255] or None
        return self


class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=5000)


class TicketMessageOut(BaseModel):
    id: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    body: str
    is_staff_reply: bool
    is_bot_reply: bool = False
    attachment_url: Optional[str] = None
    attachment_filename: Optional[str] = None
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
    source: str = "job_portal"
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


class SupportAttachmentOut(BaseModel):
    url: str
    filename: str


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
    admin_reply: Optional[str] = None
    admin_replied_at: Optional[datetime] = None
    admin_replier_name: Optional[str] = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return _utc_iso(value)

    @field_serializer('admin_replied_at')
    def serialize_admin_replied_at(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_iso(value) if value else None

    class Config:
        from_attributes = True


class FeedbackReplyCreate(BaseModel):
    message: str = Field(..., min_length=2, max_length=5000)


class FeedbackListResponse(BaseModel):
    items: List[FeedbackOut]
    total: int


class InquiryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    subject: Optional[str] = Field(None, max_length=200)
    message: str = Field(..., min_length=5, max_length=5000)


class InquiryOut(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
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
