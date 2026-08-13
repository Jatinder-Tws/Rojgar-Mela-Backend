import re
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
    payment_status: Literal["paid_online", "paid_offline", "pending", "free", "overdue", "refunded", "initiated"] = "pending"
    payment_mode: Optional[str] = None
    total_fee: float = 0
    paid_amount: float = 0
    balance_due: float = 0
    installments: list[dict[str, Any]] = Field(default_factory=list)
    voter_card_url: Optional[str] = None
    laptop_confirmed: bool = False
    notes: Optional[str] = None
    payment_method_route: Optional[Literal["upi", "card", "emi", "offline", "email"]] = None
    batch_id: Optional[str] = None


class PortalEnrollmentUpdate(BaseModel):
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    payment_status: Optional[Literal["paid_online", "paid_offline", "pending", "free", "overdue", "refunded", "initiated"]] = None
    payment_mode: Optional[str] = None
    paid_amount: Optional[float] = None
    balance_due: Optional[float] = None
    voter_card_url: Optional[str] = None
    laptop_confirmed: Optional[bool] = None
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
    voter_card_url: Optional[str] = None
    laptop_confirmed: bool = False
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

# Calendar Week view only renders an 8:00 AM–8:00 PM grid (ScheduleCalendar.tsx),
# so scheduled times must stay within that window or they render clipped/hidden.
WORKING_HOURS_START_MINUTES = 8 * 60
WORKING_HOURS_END_MINUTES = 20 * 60

_TIME_12H_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.IGNORECASE)


def time_within_working_hours(value: str) -> bool:
    match = _TIME_12H_PATTERN.match(value.strip())
    if not match:
        return False
    hour = int(match.group(1))
    minute = int(match.group(2))
    period = match.group(3).upper()
    if hour < 1 or hour > 12 or minute < 0 or minute > 59:
        return False
    if period == "PM" and hour != 12:
        hour += 12
    if period == "AM" and hour == 12:
        hour = 0
    minutes = hour * 60 + minute
    return WORKING_HOURS_START_MINUTES <= minutes <= WORKING_HOURS_END_MINUTES


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
    # When creating a one-date override for a recurring series, ignore the parent row.
    ignore_session_id: Optional[str] = None


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
    ignore_session_id: Optional[str] = None


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
    live_occurrence_date: Optional[str] = None
    occurrence_date: Optional[str] = None
    can_start: bool = False
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    session_report: Optional[str] = None
    covered_topic_ids: list[str] = Field(default_factory=list)
    attachment_url: Optional[str] = None
    attachment_filename: Optional[str] = None
    reminder_sent: bool = False
    reminder_15_sent: bool = False
    end_reminder_sent: bool = False
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
    attachment_url: Optional[str] = None
    attachment_filename: Optional[str] = None
    late_start_reason: Optional[str] = None
    early_end_reason: Optional[str] = None
    instructor_name: Optional[str] = None
    occurrence_date: Optional[str] = None


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


# ── Behavior reports ──────────────────────────────────────────────────────────

class PortalBehaviorReportCreate(BaseModel):
    enrollment_id: str
    discipline_rating: int
    participation_rating: int
    performance_rating: int
    comments: str
    report_date: Optional[str] = None


class PortalBehaviorReportOut(BaseModel):
    id: str
    enrollment_id: Optional[str] = None
    candidate_name: str
    candidate_email: str
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    instructor_id: Optional[str] = None
    instructor_name: str
    teacher_email: Optional[str] = None
    date: str
    discipline_rating: int
    participation_rating: int
    performance_rating: int
    comments: str
    flagged_for_review: bool = False
    created_at: datetime
    updated_at: datetime


# ── Notifications ─────────────────────────────────────────────────────────────

class PortalNotificationOut(BaseModel):
    id: str
    candidate_email: str
    recipient_role: str
    is_read: bool
    type: str
    title: str
    description: str
    detail: Optional[str] = None
    date: str
    severity: str
    created_at: datetime


class PortalNotificationMarkRead(BaseModel):
    notification_ids: Optional[list[str]] = None



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
    transaction_reference: Optional[str] = None
    bank_name: Optional[str] = None
    notes: Optional[str] = None
    date: Optional[str] = None
    installment_number: Optional[int] = None


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
    transaction_reference: Optional[str] = None
    bank_name: Optional[str] = None
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class PortalInvoiceLineItem(BaseModel):
    label: str
    amount: float


class PortalPaymentInvoiceOut(BaseModel):
    invoice_number: str
    transaction_id: str
    transaction_type: str
    invoice_date: datetime
    generated_at: datetime
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str] = None
    program_title: str
    batch_name: Optional[str] = None
    payment_mode: Optional[str] = None
    provider: Optional[str] = None
    provider_transaction_id: Optional[str] = None
    reference_order_id: Optional[str] = None
    transaction_reference: Optional[str] = None
    bank_name: Optional[str] = None
    status: str
    currency: str
    amount: float
    total_fee: float
    paid_amount: float
    balance_due: float
    enrollment_date: str
    notes: Optional[str] = None
    issuer_label: str = "RojgarMela Training Portal"
    line_items: list[PortalInvoiceLineItem] = Field(default_factory=list)
    base_fee: Optional[float] = None
    emi_interest_amount: Optional[float] = None
    emi_interest_percent: Optional[float] = None
    transactions: list[PortalTransactionOut] = Field(default_factory=list)


# ── Dashboard summary ─────────────────────────────────────────────────────────

class PortalWeeklyFeePoint(BaseModel):
    key: str
    label: str
    collected: float
    pending: float


class PortalTeacherWorkloadPoint(BaseModel):
    teacher_key: str
    teacher_name: str
    batch_count: int
    ongoing_count: int
    seats_filled: int = 0


class PortalCourseEnrollmentPoint(BaseModel):
    course_id: str
    count: int


class PortalBatchPerformancePoint(BaseModel):
    batch_id: str
    batch_name: str
    student_count: int
    avg_attendance: int
    avg_completion: int
    utilization: int


class PortalEnrollmentStatusCounts(BaseModel):
    active: int = 0
    completed: int = 0
    dropped: int = 0
    pending: int = 0


class PortalPaymentStatusCounts(BaseModel):
    paid: int = 0
    pending: int = 0
    overdue: int = 0
    paid_percent: int = 0
    pending_percent: int = 0
    overdue_percent: int = 0


class PortalLeaveStatsCounts(BaseModel):
    pending: int = 0
    approved: int = 0
    rejected: int = 0
    total: int = 0


class PortalBehaviorAvg(BaseModel):
    discipline: float = 0
    participation: float = 0
    performance: float = 0
    overall: float = 0


class PortalDashboardSummaryOut(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    total_students: int = 0
    total_enrollments: int = 0
    total_teachers: int = 0
    active_teachers: int = 0
    total_courses: int = 0
    total_internships: int = 0
    active_batches: int = 0
    upcoming_batches: int = 0
    completed_batches: int = 0
    total_batches: int = 0
    total_seats: int = 0
    filled_seats: int = 0
    batch_utilization_percent: int = 0
    fee_collection: float = 0
    pending_fee: float = 0
    overdue_count: int = 0
    certificates_issued: int = 0
    certificate_eligible: int = 0
    today_classes_count: int = 0
    total_scheduled_classes: int = 0
    avg_attendance: int = 0
    avg_completion: int = 0
    at_risk_count: int = 0
    attendance_compliant: int = 0
    attendance_below_threshold: int = 0
    enrollment_status: PortalEnrollmentStatusCounts = Field(default_factory=PortalEnrollmentStatusCounts)
    payment_status: PortalPaymentStatusCounts = Field(default_factory=PortalPaymentStatusCounts)
    leave_stats: PortalLeaveStatsCounts = Field(default_factory=PortalLeaveStatsCounts)
    behavior_avg: PortalBehaviorAvg = Field(default_factory=PortalBehaviorAvg)
    weekly_fee: list[PortalWeeklyFeePoint] = Field(default_factory=list)
    teacher_workload: list[PortalTeacherWorkloadPoint] = Field(default_factory=list)
    course_enrollment: list[PortalCourseEnrollmentPoint] = Field(default_factory=list)
    batch_performance: list[PortalBatchPerformancePoint] = Field(default_factory=list)

