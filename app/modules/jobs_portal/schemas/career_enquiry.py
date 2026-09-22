from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

VALID_ENQUIRY_STATUSES = {
    "new",
    "contacted",
    "follow_up_required",
    "visit_scheduled",
    "counselling_done",
    "converted",
    "lost",
    # Legacy values still accepted until rows are remapped
    "in_progress",
    "enrolled",
    "not_interested",
    "closed",
}

STATUS_ALIASES = {
    "in_progress": "follow_up_required",
    "enrolled": "converted",
    "not_interested": "lost",
    "closed": "lost",
}

VALID_FEE_INTEREST = {"yes", "no", "maybe", ""}

EnquirySource = Literal["career", "contact"]


def normalize_enquiry_status(status: Optional[str]) -> str:
    raw = (status or "new").strip().lower()
    return STATUS_ALIASES.get(raw, raw)


def _utc_iso(dt: datetime) -> str:
    if dt is None:
        return ""
    return dt.isoformat() + "Z"


def _optional_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat() + "Z"


class CareerEnquiryCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=150)
    phone: str = Field(..., min_length=10, max_length=20)
    qualification: str = Field(..., min_length=1, max_length=100)
    domain: str = Field(..., min_length=1, max_length=150)
    message: Optional[str] = Field(None, max_length=2000)


class CareerEnquiryStatusUpdate(BaseModel):
    status: Optional[str] = Field(None, min_length=1, max_length=40)
    admin_notes: Optional[str] = Field(None, max_length=5000)
    last_contact_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None
    preferred_call_time: Optional[str] = Field(None, max_length=120)
    interested_after_fee: Optional[str] = Field(None, max_length=20)
    main_objection: Optional[str] = Field(None, max_length=255)
    final_outcome: Optional[str] = Field(None, max_length=2000)
    clear_last_contact_date: bool = False
    clear_next_follow_up_date: bool = False
    source: EnquirySource = "career"

    @field_validator("interested_after_fee")
    @classmethod
    def validate_fee_interest(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in VALID_FEE_INTEREST:
            raise ValueError("interested_after_fee must be yes, no, or maybe")
        return normalized or None


class CareerEnquiryOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    qualification: str
    domain: str
    message: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    last_contact_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None
    preferred_call_time: Optional[str] = None
    interested_after_fee: Optional[str] = None
    main_objection: Optional[str] = None
    final_outcome: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value)

    @field_serializer("last_contact_date", "next_follow_up_date")
    def serialize_optional_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _optional_utc_iso(value)

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
    last_contact_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None
    preferred_call_time: Optional[str] = None
    interested_after_fee: Optional[str] = None
    main_objection: Optional[str] = None
    final_outcome: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return _utc_iso(value)

    @field_serializer("last_contact_date", "next_follow_up_date")
    def serialize_optional_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _optional_utc_iso(value)

    class Config:
        from_attributes = True


class CareerEnquiryListResponse(BaseModel):
    items: List[UnifiedEnquiryOut]
    total: int
    page: int = 1
    page_size: int = 10


class EnquiryPipelineStats(BaseModel):
    total: int = 0
    active: int = 0
    follow_up_due_today: int = 0
    visit_scheduled: int = 0
    converted: int = 0
    lost: int = 0
    by_status: Dict[str, int] = Field(default_factory=dict)
