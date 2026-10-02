from datetime import datetime
import re
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
    consent_to_contact: Optional[bool] = None
    ticket_number: Optional[str] = None
    is_event_winner: bool = False
    event_title: Optional[str] = None
    draw_date: Optional[str] = None
    announcement_id: Optional[str] = None
    location: Optional[str] = None
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


class AdminManualEnquiryCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    phone: str = Field(..., min_length=7, max_length=20)
    email: str = Field(..., min_length=5, max_length=150)
    city: Optional[str] = Field(None, max_length=80)
    preferred_contact: Optional[str] = Field(None, max_length=40)
    programme: str = Field(..., min_length=1, max_length=150)
    lead_source: Optional[str] = Field(None, max_length=80)
    enquiry_date: Optional[str] = None
    campaign_code: Optional[str] = Field(None, max_length=80)
    message: Optional[str] = Field(None, max_length=2000)
    status: str = "new"
    assigned_counsellor: Optional[str] = Field(None, max_length=120)
    priority: Optional[str] = Field(None, max_length=20)
    check_duplicates: bool = True
    next_follow_up_date: Optional[str] = None
    follow_up_time: Optional[str] = Field(None, max_length=20)
    follow_up_mode: Optional[str] = Field(None, max_length=40)
    follow_up_note: Optional[str] = Field(None, max_length=2000)
    remarks: Optional[str] = Field(None, max_length=2000)
    consent_to_contact: bool

    @field_validator("first_name", "last_name", "phone", "email", "programme", mode="before")
    @classmethod
    def strip_manual_required_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def validate_manual_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address")
        return value.lower()

    @field_validator("phone")
    @classmethod
    def validate_manual_phone(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if not 7 <= len(digits) <= 15:
            raise ValueError("Phone must contain 7 to 15 digits")
        return value

    @field_validator("follow_up_time")
    @classmethod
    def validate_follow_up_time(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return value
        if not re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d", value.strip()):
            raise ValueError("Follow-up time must use HH:mm format")
        return value.strip()

    @field_validator("consent_to_contact")
    @classmethod
    def require_contact_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent to contact is required")
        return value


class EnquiryImportResult(BaseModel):
    created: int = 0
    skipped: int = 0
    failed: int = 0
    errors: List[str] = Field(default_factory=list)


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
