from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

FIELD_TYPES = {"text", "email", "phone", "textarea", "select", "radio_cards", "number"}


def _utc_iso(dt: datetime) -> str:
    if dt is None:
        return ""
    return dt.isoformat() + "Z"


def _optional_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat() + "Z"


class EventFormFieldOption(BaseModel):
    value: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=240)
    icon: Optional[str] = Field(None, max_length=40)


class EventFormField(BaseModel):
    id: str = Field(..., min_length=1, max_length=80)
    key: str = Field(..., min_length=1, max_length=80)
    type: str = Field(..., min_length=1, max_length=40)
    label: str = Field(..., min_length=1, max_length=160)
    required: bool = False
    placeholder: Optional[str] = Field(None, max_length=160)
    help_text: Optional[str] = Field(None, max_length=240)
    options: List[EventFormFieldOption] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in FIELD_TYPES:
            raise ValueError(f"Unsupported field type: {value}")
        return normalized

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        cleaned = value.strip().lower().replace(" ", "_")
        if not cleaned:
            raise ValueError("Field key is required")
        return cleaned


class EventPrizeIn(BaseModel):
    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=80)
    worth_value: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=2000)
    total_inventory: int = Field(0, ge=0, le=100000)
    remaining_inventory: Optional[int] = Field(None, ge=0, le=100000)
    win_weight: int = Field(10, ge=1, le=100)
    voucher_expiry_days: Optional[int] = Field(None, ge=0, le=3650)
    redemption_instructions: Optional[str] = Field(None, max_length=2000)
    is_active: bool = True
    sort_order: int = Field(0, ge=0, le=10000)


class EventPrizeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=80)
    worth_value: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=2000)
    total_inventory: Optional[int] = Field(None, ge=0, le=100000)
    remaining_inventory: Optional[int] = Field(None, ge=0, le=100000)
    win_weight: Optional[int] = Field(None, ge=1, le=100)
    voucher_expiry_days: Optional[int] = Field(None, ge=0, le=3650)
    redemption_instructions: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0, le=10000)


class EventPrizeOut(BaseModel):
    id: str
    form_id: str
    title: str
    category: Optional[str] = None
    worth_value: Optional[str] = None
    description: Optional[str] = None
    total_inventory: int
    remaining_inventory: int
    win_weight: int
    voucher_expiry_days: Optional[int] = None
    redemption_instructions: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class EventFormBase(BaseModel):
    event_name: str = Field(..., min_length=2, max_length=200)
    booth_location: Optional[str] = Field(None, max_length=200)
    headline: str = Field("Get Your Lucky Scratch Ticket", min_length=2, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=500)
    badge_label: Optional[str] = Field(None, max_length=80)
    cta_label: str = Field("Register & Get Random Lucky Ticket", min_length=2, max_length=120)
    ticket_prefix: str = Field("TKT", min_length=2, max_length=12)
    lucky_draw_enabled: bool = True
    is_active: bool = True
    fields: List[EventFormField] = Field(default_factory=list)
    thank_you_message: Optional[str] = Field(None, max_length=500)

    @field_validator("ticket_prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        cleaned = "".join(ch for ch in value.upper() if ch.isalnum())[:12]
        if len(cleaned) < 2:
            raise ValueError("Ticket prefix must contain at least 2 letters or digits")
        return cleaned


class EventFormCreate(EventFormBase):
    slug: Optional[str] = Field(None, max_length=80)
    prizes: List[EventPrizeIn] = Field(default_factory=list)


class EventFormUpdate(BaseModel):
    event_name: Optional[str] = Field(None, min_length=2, max_length=200)
    booth_location: Optional[str] = Field(None, max_length=200)
    headline: Optional[str] = Field(None, min_length=2, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=500)
    badge_label: Optional[str] = Field(None, max_length=80)
    cta_label: Optional[str] = Field(None, min_length=2, max_length=120)
    ticket_prefix: Optional[str] = Field(None, min_length=2, max_length=12)
    lucky_draw_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    fields: Optional[List[EventFormField]] = None
    thank_you_message: Optional[str] = Field(None, max_length=500)
    slug: Optional[str] = Field(None, max_length=80)
    prizes: Optional[List[EventPrizeIn]] = None

    @field_validator("ticket_prefix")
    @classmethod
    def validate_prefix(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = "".join(ch for ch in value.upper() if ch.isalnum())[:12]
        if len(cleaned) < 2:
            raise ValueError("Ticket prefix must contain at least 2 letters or digits")
        return cleaned


class EventFormOut(BaseModel):
    id: str
    slug: str
    event_name: str
    booth_location: Optional[str] = None
    headline: str
    subtitle: Optional[str] = None
    badge_label: Optional[str] = None
    cta_label: str
    ticket_prefix: str
    lucky_draw_enabled: bool
    is_active: bool
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    thank_you_message: Optional[str] = None
    prizes: List[EventPrizeOut] = Field(default_factory=list)
    submission_count: int = 0
    verified_count: int = 0
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class EventFormListResponse(BaseModel):
    items: List[EventFormOut]
    total: int
    page: int
    page_size: int


class EventFormPublicOut(BaseModel):
    slug: str
    event_name: str
    booth_location: Optional[str] = None
    headline: str
    subtitle: Optional[str] = None
    badge_label: Optional[str] = None
    cta_label: str
    lucky_draw_enabled: bool
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    thank_you_message: Optional[str] = None


class EventRegisterIn(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict)


class EventRegisterPendingOut(BaseModel):
    pending_id: str
    email_hint: str
    message: str


class EventVerifyOtpIn(BaseModel):
    pending_id: str = Field(..., min_length=8, max_length=80)
    otp: str = Field(..., min_length=4, max_length=8)


class EventResendOtpIn(BaseModel):
    pending_id: str = Field(..., min_length=8, max_length=80)


class EventTicketOut(BaseModel):
    pending_id: str
    ticket_number: str
    event_name: str
    booth_location: Optional[str] = None
    full_name: str
    email: str
    lucky_draw_enabled: bool
    is_winner: bool
    prize_title: Optional[str] = None
    prize_category: Optional[str] = None
    prize_worth: Optional[str] = None
    prize_description: Optional[str] = None
    redemption_instructions: Optional[str] = None
    thank_you_message: Optional[str] = None


class EventSubmissionOut(BaseModel):
    id: str
    form_id: str
    enquiry_id: Optional[str] = None
    full_name: str
    email: str
    phone: str
    visitor_role: Optional[str] = None
    organization: Optional[str] = None
    interest: Optional[str] = None
    email_verified: bool
    ticket_number: Optional[str] = None
    prize_title: Optional[str] = None
    prize_category: Optional[str] = None
    prize_worth: Optional[str] = None
    is_winner: bool
    created_at: datetime
    verified_at: Optional[datetime] = None

    @field_serializer("created_at", "verified_at")
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _optional_utc_iso(value)

    class Config:
        from_attributes = True


class EventSubmissionListResponse(BaseModel):
    items: List[EventSubmissionOut]
    total: int
    page: int
    page_size: int


class EventTestDrawOut(BaseModel):
    prize_title: Optional[str] = None
    prize_category: Optional[str] = None
    remaining_inventory: Optional[int] = None
    message: str


DEFAULT_PTC_FIELDS: List[Dict[str, Any]] = [
    {
        "id": "fld_full_name",
        "key": "full_name",
        "type": "text",
        "label": "Full Name",
        "required": True,
        "placeholder": "e.g. Rahul Sharma",
        "help_text": None,
        "options": [],
    },
    {
        "id": "fld_phone",
        "key": "phone",
        "type": "phone",
        "label": "Phone Number",
        "required": True,
        "placeholder": "+91 98765 43210",
        "help_text": None,
        "options": [],
    },
    {
        "id": "fld_email",
        "key": "email",
        "type": "email",
        "label": "Email Address",
        "required": True,
        "placeholder": "rahul@example.com",
        "help_text": None,
        "options": [],
    },
    {
        "id": "fld_visitor_role",
        "key": "visitor_role",
        "type": "radio_cards",
        "label": "I am visiting this stall as",
        "required": True,
        "placeholder": "Select your primary role",
        "help_text": None,
        "options": [
            {
                "value": "Learner / Seeker",
                "label": "Learner / Seeker",
                "description": "Looking for jobs, bootcamps, courses & certifications",
                "icon": "graduation-cap",
            },
            {
                "value": "Teacher / Faculty",
                "label": "Teacher / Faculty",
                "description": "Educators looking for student programs & curriculum",
                "icon": "book-open",
            },
            {
                "value": "Industry Mentor",
                "label": "Industry Mentor",
                "description": "Professionals wanting to mentor, teach or review projects",
                "icon": "lightbulb",
            },
            {
                "value": "Resource Provider",
                "label": "Resource Provider",
                "description": "Offering tools, learning content, or educational services",
                "icon": "wrench",
            },
            {
                "value": "Strategic Partner",
                "label": "Strategic Partner",
                "description": "College dean, company HR, recruitment or institutional MoU",
                "icon": "handshake",
            },
        ],
    },
    {
        "id": "fld_organization",
        "key": "organization",
        "type": "text",
        "label": "College / Company / Institution (Optional)",
        "required": False,
        "placeholder": "e.g. Delhi Technological University / Infosys",
        "help_text": None,
        "options": [],
    },
]
