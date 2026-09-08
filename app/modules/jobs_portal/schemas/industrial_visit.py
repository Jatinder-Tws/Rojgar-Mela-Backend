from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator

DEPARTMENTS = [
    "CSE",
    "IT",
    "ECE",
    "EE",
    "ME",
    "Civil",
    "Chemical",
    "Biotechnology",
    "BCA",
    "MCA",
    "BBA",
    "MBA",
    "Other",
]

YEARS_OF_STUDY = [
    "1st Year",
    "2nd Year",
    "3rd Year",
    "4th Year",
    "Other",
]

AttendanceStatus = Literal["pending", "present"]
CertificateStatus = Literal["pending", "sent", "failed"]


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat() + "Z"


class IndustrialVisitRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    college_name: str = Field(..., min_length=2, max_length=200)
    department: str = Field(..., min_length=1, max_length=120)
    year_of_study: str = Field(..., min_length=1, max_length=40)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    location: str = Field(..., min_length=2, max_length=120)
    area_of_interest: str = Field(..., min_length=2, max_length=500)
    graduation_year: str = Field(..., min_length=4, max_length=10)

    @field_validator("full_name", "college_name", "location", "area_of_interest", "department", "year_of_study")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("This field is required")
        return cleaned

    @field_validator("department")
    @classmethod
    def validate_department(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Enter your department or branch")
        return cleaned

    @field_validator("area_of_interest")
    @classmethod
    def validate_interests(cls, value: str) -> str:
        tags = [part.strip() for part in value.split(",") if part.strip()]
        if not tags:
            raise ValueError("Add at least one area of interest")
        if len(tags) > 8:
            raise ValueError("You can add up to 8 areas of interest")
        cleaned: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            if len(tag) < 2:
                raise ValueError("Each interest must be at least 2 characters")
            if len(tag) > 40:
                raise ValueError("Each interest must be 40 characters or less")
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(tag)
        return ", ".join(cleaned)

    @field_validator("year_of_study")
    @classmethod
    def validate_year(cls, value: str) -> str:
        if value not in YEARS_OF_STUDY:
            raise ValueError(f"Invalid year of study. Allowed: {', '.join(YEARS_OF_STUDY)}")
        return value

    @field_validator("graduation_year")
    @classmethod
    def validate_grad_year(cls, value: str) -> str:
        digits = (value or "").strip()
        if not digits.isdigit() or len(digits) != 4:
            raise ValueError("Enter a valid 4-digit graduation year")
        year = int(digits)
        current = datetime.utcnow().year
        if year < 2020 or year > current + 6:
            raise ValueError(f"Graduation year must be between 2020 and {current + 6}")
        return digits


class IndustrialVisitCheckIn(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)

    @field_validator("phone")
    @classmethod
    def strip_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class IndustrialVisitCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    visit_date: datetime
    venue: Optional[str] = Field(None, max_length=300)
    college_name: Optional[str] = Field(None, max_length=200)
    is_active: bool = True


class IndustrialVisitUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    visit_date: Optional[datetime] = None
    venue: Optional[str] = Field(None, max_length=300)
    college_name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class IndustrialVisitAttendanceUpdate(BaseModel):
    attendance_status: AttendanceStatus


class IndustrialVisitPublicOut(BaseModel):
    id: str
    title: str
    visit_date: datetime
    venue: Optional[str] = None
    college_name: Optional[str] = None
    slug: str
    is_active: bool

    @field_serializer("visit_date")
    def serialize_visit_date(self, value: datetime) -> str:
        return _utc_iso(value) or ""

    class Config:
        from_attributes = True


class IndustrialVisitCheckInPublicOut(BaseModel):
    id: str
    title: str
    visit_date: datetime
    venue: Optional[str] = None
    is_active: bool

    @field_serializer("visit_date")
    def serialize_visit_date(self, value: datetime) -> str:
        return _utc_iso(value) or ""

    class Config:
        from_attributes = True


class IndustrialVisitRegisterOut(BaseModel):
    id: str
    full_name: str
    email: str
    message: str


class IndustrialVisitCheckInOut(BaseModel):
    already_present: bool
    full_name: str
    message: str


class IndustrialVisitStats(BaseModel):
    registered: int = 0
    present: int = 0
    pending: int = 0
    certificates_sent: int = 0


class IndustrialVisitAdminOut(BaseModel):
    id: str
    title: str
    visit_date: datetime
    venue: Optional[str] = None
    college_name: Optional[str] = None
    slug: str
    check_in_slug: str
    is_active: bool
    certificates_sent_at: Optional[datetime] = None
    registration_url: str
    check_in_url: str
    stats: IndustrialVisitStats = Field(default_factory=IndustrialVisitStats)
    created_at: datetime
    updated_at: datetime

    @field_serializer("visit_date", "certificates_sent_at", "created_at", "updated_at")
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class IndustrialVisitAdminListResponse(BaseModel):
    items: List[IndustrialVisitAdminOut]
    total: int
    page: int = 1
    page_size: int = 10


class IndustrialVisitStudentOut(BaseModel):
    id: str
    visit_id: str
    full_name: str
    college_name: str
    department: str
    year_of_study: str
    email: str
    phone: str
    location: str
    area_of_interest: str
    graduation_year: str
    attendance_status: str
    attended_at: Optional[datetime] = None
    certificate_status: str
    certificate_sent_at: Optional[datetime] = None
    certificate_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("attended_at", "certificate_sent_at", "created_at", "updated_at")
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_iso(value)

    class Config:
        from_attributes = True


class IndustrialVisitStudentListResponse(BaseModel):
    items: List[IndustrialVisitStudentOut]
    total: int
    page: int = 1
    page_size: int = 10
    stats: IndustrialVisitStats = Field(default_factory=IndustrialVisitStats)


class IndustrialVisitSendCertificatesOut(BaseModel):
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    message: str


class IndustrialVisitCertificateVerifyOut(BaseModel):
    valid: bool
    certificate_id: Optional[str] = None
    full_name: Optional[str] = None
    college_name: Optional[str] = None
    department: Optional[str] = None
    visit_title: Optional[str] = None
    visit_date: Optional[datetime] = None
    venue: Optional[str] = None
    issued_at: Optional[datetime] = None

    @field_serializer("visit_date", "issued_at")
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_iso(value)
