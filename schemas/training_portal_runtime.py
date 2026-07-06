from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ── Payment settings ──────────────────────────────────────────────────────────

class PortalPaymentSettingsOut(BaseModel):
    upi: bool
    card: bool
    emi: bool
    offline: bool
    email: bool
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortalPaymentSettingsUpdate(BaseModel):
    upi: Optional[bool] = None
    card: Optional[bool] = None
    emi: Optional[bool] = None
    offline: Optional[bool] = None
    email: Optional[bool] = None


# ── Installments ──────────────────────────────────────────────────────────────

class InstallmentOut(BaseModel):
    id: str
    number: int
    amount: float
    due_date: str
    status: Literal["pending", "paid", "overdue"]
    paid_date: Optional[str] = None
    payment_mode: Optional[str] = None
    recorded_by: Optional[str] = None
    receipt_number: Optional[str] = None


# ── Enrollments ───────────────────────────────────────────────────────────────

class PortalEnrollmentCreate(BaseModel):
    enrollment_type: Literal["course", "internship"]
    item_id: str
    title: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    payment_type: Literal["Free", "Full Payment", "EMI"] = "Full Payment"
    payment_status: Literal["paid_online", "paid_offline", "pending", "free", "overdue", "refunded"] = "pending"
    payment_mode: Optional[str] = None
    total_fee: float = 0
    paid_amount: float = 0
    balance_due: float = 0
    installments: list[dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    payment_method_route: Optional[Literal["upi", "card", "emi", "offline", "email"]] = None
    batch_id: Optional[str] = None


class PortalEnrollmentUpdate(BaseModel):
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    payment_status: Optional[Literal["paid_online", "paid_offline", "pending", "free", "overdue", "refunded"]] = None
    payment_mode: Optional[str] = None
    paid_amount: Optional[float] = None
    balance_due: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[Literal["active", "completed", "dropped", "pending"]] = None
    attendance_percentage: Optional[int] = None
    completion_percentage: Optional[int] = None
    is_certificate_issued: Optional[bool] = None


class PortalEnrollmentOut(BaseModel):
    id: str
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str] = None
    type: str
    item_id: str
    batch_id: Optional[str] = None
    title: str
    batch_name: Optional[str] = None
    enrollment_date: str
    payment_type: str
    payment_status: str
    payment_mode: Optional[str] = None
    total_fee: float
    paid_amount: float
    balance_due: float
    installments: list[dict[str, Any]] = Field(default_factory=list)
    status: str
    attendance_percentage: int
    completion_percentage: int
    is_certificate_issued: bool
    certificate_id: Optional[str] = None
    certificate_status: Optional[str] = None
    certificate_reason: Optional[str] = None
    notes: Optional[str] = None
    preferred_batch_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Batches ───────────────────────────────────────────────────────────────────

class PortalBatchCreate(BaseModel):
    course_id: str
    batch_name: str = Field(..., min_length=1, max_length=200)
    instructor_id: Optional[str] = None
    instructor_name: str = Field(..., min_length=1)
    start_date: str
    end_date: str
    days: list[str] = Field(default_factory=list)
    time: str = "To be scheduled"
    venue: str = "To be scheduled"
    max_seats: int = Field(ge=1)
    delivery_mode: Literal["Offline", "Online", "Hybrid"] = "Offline"
    status: Literal["upcoming", "ongoing", "completed"] = "upcoming"
    enrollment_ids: list[str] = Field(default_factory=list)


class PortalBatchOut(BaseModel):
    id: str
    course_id: str
    batch_name: str
    instructor_id: Optional[str] = None
    instructor_name: str
    start_date: str
    end_date: str
    days: list[str]
    time: str
    venue: str
    max_seats: int
    seats_filled: int
    delivery_mode: str
    status: str
    covered_topics: list[str] = Field(default_factory=list)
    enrollment_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PortalBatchUpdate(BaseModel):
    batch_name: Optional[str] = Field(None, min_length=1, max_length=200)
    instructor_id: Optional[str] = None
    instructor_name: Optional[str] = Field(None, min_length=1)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days: Optional[list[str]] = None
    time: Optional[str] = None
    venue: Optional[str] = None
    max_seats: Optional[int] = Field(None, ge=1)
    delivery_mode: Optional[Literal["Offline", "Online", "Hybrid"]] = None
    status: Optional[Literal["upcoming", "ongoing", "completed"]] = None
    enrollment_ids: Optional[list[str]] = None


# ── Class sessions ────────────────────────────────────────────────────────────

class PortalClassSessionCreate(BaseModel):
    batch_id: Optional[str] = None
    item_id: str
    title: str
    instructor_name: str
    date: str
    start_time: str
    end_time: str
    days: list[str] = Field(default_factory=list)
    venue: Optional[str] = None
    note: Optional[str] = None
    schedule_type: Literal["one_time", "recurring"] = "one_time"
    postponed: bool = False
    teacher_unavailable: bool = False
    admin_override: bool = False


class PortalClassSessionUpdate(BaseModel):
    batch_id: Optional[str] = None
    item_id: Optional[str] = None
    title: Optional[str] = None
    instructor_name: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    days: Optional[list[str]] = None
    venue: Optional[str] = None
    note: Optional[str] = None
    schedule_type: Optional[Literal["one_time", "recurring"]] = None
    postponed: Optional[bool] = None
    teacher_unavailable: Optional[bool] = None
    admin_override: bool = False


class PortalClassSessionOut(BaseModel):
    id: str
    batch_id: Optional[str] = None
    item_id: str
    title: str
    instructor_name: str
    date: str
    start_time: str
    end_time: str
    days: list[str]
    venue: Optional[str] = None
    note: Optional[str] = None
    schedule_type: str
    postponed: bool
    teacher_unavailable: bool
    live_status: str = "scheduled"
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    session_report: Optional[str] = None
    covered_topic_ids: list[str] = Field(default_factory=list)
    reminder_sent: bool = False
    reminder_15_sent: bool = False
    late_start_reason: Optional[str] = None
    early_end_reason: Optional[str] = None
    attendance_marked: bool = False
    created_at: datetime
    updated_at: datetime


class PortalSessionStudentOut(BaseModel):
    enrollment_id: str
    candidate_name: str
    candidate_email: str
    approved_leave: bool = False


class PortalClassSessionStart(BaseModel):
    late_start_reason: Optional[str] = None


class PortalAttendanceEntry(BaseModel):
    enrollment_id: str
    status: Literal["present", "absent", "late", "on_leave"]


class PortalClassSessionComplete(BaseModel):
    attendance: list[PortalAttendanceEntry]
    session_report: Optional[str] = None
    covered_topic_ids: list[str] = Field(default_factory=list)
    early_end_reason: Optional[str] = None


class PortalAttendanceRecordOut(BaseModel):
    id: str
    class_session_id: str
    enrollment_id: str
    batch_id: Optional[str] = None
    candidate_email: str
    candidate_name: str
    status: str
    marked_at: datetime
    session_title: Optional[str] = None
    session_date: Optional[str] = None
    session_start_time: Optional[str] = None
    session_end_time: Optional[str] = None
    session_report: Optional[str] = None
    covered_topic_ids: list[str] = Field(default_factory=list)
    late_start_reason: Optional[str] = None
    early_end_reason: Optional[str] = None
    instructor_name: Optional[str] = None


# ── Leave requests ────────────────────────────────────────────────────────────

class PortalLeaveRequestCreate(BaseModel):
    session_id: Optional[str] = None
    date: str
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    reason: str


class PortalTeacherLeaveRequestCreate(BaseModel):
    date: str
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    reason: str


class PortalLeaveRequestReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: Optional[str] = None


class PortalLeaveRequestOut(BaseModel):
    id: str
    requester_type: str
    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    teacher_email: Optional[str] = None
    teacher_name: Optional[str] = None
    session_id: Optional[str] = None
    date: str
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    reason: str
    status: str
    reviewed_by_role: Optional[str] = None
    review_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Notifications ─────────────────────────────────────────────────────────────

class PortalNotificationOut(BaseModel):
    id: str
    candidate_email: str
    type: str
    title: str
    description: str
    detail: Optional[str] = None
    date: str
    severity: str
    created_at: datetime


# ── Payments ──────────────────────────────────────────────────────────────────

class PortalPaymentOrderCreate(BaseModel):
    enrollment_id: str
    payment_method: Literal["upi", "card", "emi"] = "upi"
    amount: Optional[float] = None


class PortalPaymentOrderOut(BaseModel):
    id: str
    enrollment_id: str
    amount: float
    currency: str
    payment_method: str
    status: str
    provider: str
    provider_order_id: Optional[str] = None
    razorpay_key_id: Optional[str] = None
    mock_checkout: bool = False


class PortalPaymentVerify(BaseModel):
    order_id: str
    provider_order_id: str
    provider_payment_id: str
    provider_signature: str


class PortalOfflinePaymentRecord(BaseModel):
    enrollment_id: str
    amount: float
    payment_mode: Literal["cash", "UPI", "bank_transfer"] = "UPI"
    notes: Optional[str] = None
    date: Optional[str] = None


class PortalRefundRecord(BaseModel):
    enrollment_id: str
    amount: float
    refund_mode: Literal["cash", "UPI", "bank_transfer", "gateway"] = "cash"
    notes: Optional[str] = None
    date: Optional[str] = None
    refund_via_gateway: bool = True


class PortalBatchAssignStudents(BaseModel):
    enrollment_ids: list[str] = Field(default_factory=list)


class PortalRefundRequestCreate(BaseModel):
    enrollment_id: str
    reason: str = Field(..., min_length=5, max_length=2000)
    requested_amount: Optional[float] = None


class PortalRefundRequestResolve(BaseModel):
    action: Literal["approve", "reject"]
    admin_notes: Optional[str] = None
    refund_mode: Literal["cash", "UPI", "bank_transfer", "gateway"] = "gateway"
    refund_via_gateway: bool = True


class PortalRefundRequestOut(BaseModel):
    id: str
    enrollment_id: str
    candidate_email: str
    candidate_name: str
    program_title: str
    requested_amount: float
    reason: str
    status: str
    admin_notes: Optional[str] = None
    requested_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime


class PortalTransactionOut(BaseModel):
    id: str
    transaction_id: str
    enrollment_id: Optional[str] = None
    candidate_email: str
    candidate_name: str
    program_title: str
    transaction_type: str
    amount: float
    currency: str
    payment_mode: Optional[str] = None
    status: str
    provider: Optional[str] = None
    provider_transaction_id: Optional[str] = None
    reference_order_id: Optional[str] = None
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
