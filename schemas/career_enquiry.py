from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_serializer

VALID_ENQUIRY_STATUSES = {
    "new",
    "contacted",
    "in_progress",
    "enrolled",
    "not_interested",
    "closed",
}

EnquirySource = Literal["career", "contact"]


def _utc_iso(dt: datetime) -> str:
    if dt is None:
        return ""
    return dt.isoformat() + "Z"


class CareerEnquiryCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=150)
    phone: str = Field(..., min_length=10, max_length=20)
    qualification: str = Field(..., min_length=1, max_length=100)
    domain: str = Field(..., min_length=1, max_length=150)


class CareerEnquiryStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=40)
    admin_notes: Optional[str] = Field(None, max_length=5000)
    source: EnquirySource = "career"


class CareerEnquiryOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    qualification: str
    domain: str
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class UnifiedEnquiryOut(BaseModel):
    id: str
    source: EnquirySource
    name: str
    email: str
    phone: Optional[str] = None
    qualification: Optional[str] = None
    domain: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return _utc_iso(value)

    class Config:
        from_attributes = True


class CareerEnquiryListResponse(BaseModel):
    items: List[UnifiedEnquiryOut]
    total: int
    page: int = 1
    page_size: int = 20
