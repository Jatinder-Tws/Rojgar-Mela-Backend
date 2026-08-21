from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class StudentLookupOut(BaseModel):
    exists: bool
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    qualification: Optional[str] = None
    address: Optional[str] = None
    preferred_job_sector: Optional[str] = None

    class Config:
        from_attributes = True


class AdminRegisterAndEnrollStudentCreate(BaseModel):
    # Candidate info
    email: str
    first_name: str
    last_name: str = ""
    phone: Optional[str] = None
    password: Optional[str] = None
    send_credentials: bool = True
    gender: Optional[str] = None
    qualification: Optional[str] = None
    address: Optional[str] = None
    laptop_confirmed: bool = False

    # Program / Enrollment info
    enrollment_type: Literal["course", "internship"] = "course"
    item_id: str
    title: str
    batch_id: Optional[str] = None

    # Fee & Payment info
    total_fee: float = 0.0
    paid_amount: float = 0.0
    payment_type: Literal["Full Payment", "EMI"] = "Full Payment"
    payment_mode: Optional[str] = "Cash"  # Cash, UPI, Card, Bank Transfer, Online Link, etc.
    payment_status: Optional[str] = None  # paid_offline, partially_paid, pending, etc.
    installments: list[dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    source_request_id: Optional[str] = None


class AdminRegisterAndEnrollStudentOut(BaseModel):
    message: str
    user_id: Optional[str] = None
    user_created: bool = False
    credentials_sent: bool = False
    enrollment_id: str
    candidate_email: str
    candidate_name: str
    total_fee: float
    paid_amount: float
    balance_due: float
    payment_status: str

    class Config:
        from_attributes = True
