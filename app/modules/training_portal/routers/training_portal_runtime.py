import json
import logging
import uuid
import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Optional
from fastapi.responses import StreamingResponse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status, UploadFile, File
from sqlalchemy import select, func, update, or_, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings, get_upload_dir
from app.core.database import get_db
from app.shared.models.user import User, UserRole
from app.core.dependencies import hash_password, get_current_user, require_super_admin
from app.shared.services.email_service import (
    send_welcome_email,
    send_enrollment_receipt_email,
    send_training_enrollment_receipt_email,
)
from app.modules.training_portal.schemas.training_admin_student import (
    StudentLookupOut,
    AdminRegisterAndEnrollStudentCreate,
    AdminRegisterAndEnrollStudentOut,
)
from app.modules.training_portal.models.training_portal_internship import TrainingPortalInternship
from app.modules.training_portal.models.training_portal_batch import TrainingPortalBatch
from app.modules.training_portal.models.training_portal_enrollment import TrainingPortalEnrollment
from app.modules.training_portal.models.training_portal_class_session import TrainingPortalClassSession
from app.modules.training_portal.models.training_portal_candidate_notification import TrainingPortalCandidateNotification
from app.modules.training_portal.models.training_portal_payment import TrainingPortalPaymentSettings, TrainingPortalPaymentOrder
from app.modules.training_portal.models.training_portal_transaction import TrainingPortalTransaction
from app.modules.training_portal.models.training_portal_refund_request import TrainingPortalRefundRequest
from app.modules.training_portal.models.training_portal_attendance import TrainingPortalAttendanceRecord
from app.modules.training_portal.models.training_portal_leave_request import TrainingPortalLeaveRequest
from app.modules.training_portal.models.training_portal_behavior_report import TrainingPortalBehaviorReport
from app.modules.training_portal.models.training_portal_course import TrainingPortalCourse
from app.modules.training_portal.models.training_portal_teacher import TrainingPortalTeacher
from app.modules.training_portal.schemas.training_portal_runtime import (
    PortalPaymentSettingsOut,
    PortalPaymentSettingsUpdate,
    PortalEnrollmentCreate,
    PortalEnrollmentUpdate,
    PortalEnrollmentOut,
    PortalBatchCreate,
    PortalBatchOut,
    PortalBatchUpdate,
    PortalBatchAssignStudents,
    PortalClassSessionCreate,
    PortalClassSessionUpdate,
    PortalClassSessionOut,
    PortalClassSessionComplete,
    PortalClassSessionStart,
    PortalSessionStudentOut,
    PortalAttendanceRecordOut,
    PortalLeaveRequestCreate,
    PortalTeacherLeaveRequestCreate,
    PortalLeaveRequestReview,
    PortalLeaveRequestOut,
    PortalBehaviorReportCreate,
    PortalBehaviorReportOut,
    PortalNotificationOut,
    PortalPaymentOrderCreate,
    PortalPaymentOrderOut,
    PortalPaymentVerify,
    PortalOfflinePaymentRecord,
    PortalRefundRecord,
    PortalRefundRequestCreate,
    PortalRefundRequestResolve,
    PortalRefundRequestOut,
    PortalTransactionOut,
    PortalPaymentInvoiceOut,
    PortalInvoiceLineItem,
    PortalNotificationMarkRead,
    PortalDashboardSummaryOut,
    time_within_working_hours,
)
from app.core.dependencies import require_super_admin, require_training_portal_user, require_teacher_or_super_admin
from app.modules.training_portal.services.training_portal_dashboard import build_dashboard_summary
from app.modules.training_portal.services.training_portal_mapper import (
    enrollment_to_out,
    batch_to_out,
    session_to_out,
    session_to_out_for_date,
    notification_to_out,
    payment_settings_to_out,
    payment_order_to_out,
    transaction_to_out,
    refund_request_to_out,
    leave_to_out,
    behavior_report_to_out,
)
from app.modules.training_portal.services.training_portal_payment_service import (
    create_razorpay_order,
    create_razorpay_refund,
    verify_razorpay_signature,
    verify_webhook_signature,
    parse_webhook_payment,
    razorpay_configured,
    mock_payment_ids,
)
from app.shared.services.email_service import (
    send_training_portal_batch_assigned_email,
    send_training_portal_payment_link_email,
    send_training_portal_payment_success_email,
    send_training_token_booking_receipt_email,
    send_notification_email,
)
from app.modules.training_portal.services.class_calendar_sync import (
    run_class_sync,
    run_class_cancel,
    build_cancel_snapshot,
)
from app.modules.training_portal.services.training_portal_class_live import (
    session_occurs_on_date,
    session_live_applies_to_date,
    effective_live_status,
    should_send_reminder,
    should_show_start_button,
    pending_reminder_tier,
    is_late_start,
    is_early_end,
    now_ist,
    today_ist,
    session_end_datetime,
    _parse_time_12h,
)
from app.modules.training_portal.services.training_portal_class_lifecycle import (
    process_todays_session_lifecycle,
    recalculate_batch_progress as _recalculate_batch_progress,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-portal/runtime", tags=["Training Portal Runtime"])

MIN_BATCH_SCHEDULE_STUDENTS = 15
MAX_BATCH_STUDENTS = 20
REFUND_REQUEST_MIN_DAYS = 14


def _batch_export_status(batch: TrainingPortalBatch, scheduled_class_count: int, today: str | None = None) -> str:
    current_day = today or datetime.utcnow().strftime("%Y-%m-%d")
    if batch.status == "completed" or batch.end_date < current_day:
        return "Completed"
    if batch.start_date <= current_day <= batch.end_date:
        return "Ongoing" if scheduled_class_count > 0 or batch.status == "ongoing" else "Upcoming"
    if scheduled_class_count > 0:
        return "Scheduled"
    return "Ongoing" if batch.status == "ongoing" else "Upcoming"


def _batch_export_schedule(batch: TrainingPortalBatch, sessions: list[TrainingPortalClassSession]) -> tuple[str, str]:
    batch_sessions = [session for session in sessions if session.batch_id == batch.id]
    recurring = [
        session
        for session in batch_sessions
        if (session.schedule_type or "one_time") == "recurring" and (session.days or [])
    ]
    one_time = [
        session
        for session in batch_sessions
        if (session.schedule_type or "one_time") == "one_time"
        or ((session.schedule_type or "") != "recurring" and not (session.days or []))
    ]

    if batch_sessions:
        if recurring and one_time:
            days = ", ".join(recurring[0].days or []) or "Recurring"
            time_label = f"{recurring[0].start_time} - {recurring[0].end_time}"
            return f"{days} + {len(one_time)} one-time", time_label
        if recurring:
            days = ", ".join(recurring[0].days or []) or "Recurring"
            if len(recurring) > 1:
                days = f"{days} + {len(recurring)} series"
            time_label = f"{recurring[0].start_time} - {recurring[0].end_time}"
            return days, time_label
        primary = one_time[0]
        time_label = f"{primary.start_time} - {primary.end_time}"
        if len(one_time) == 1:
            return "One-time", time_label
        return f"{len(one_time)} one-time classes", time_label

    days_label = ", ".join(batch.days or []) if batch.days else f"{batch.start_date} to {batch.end_date}"
    time_label = batch.time_slot or "To be scheduled"
    return days_label, time_label


@router.post("/enrollments/voter-card", response_model=dict)
async def upload_voter_card(
    file: UploadFile = File(...),
    current_user: User = Depends(require_training_portal_user),
):
    ext = Path(file.filename or "voter-card").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .jpg, .jpeg, .png, .webp, or .pdf files are allowed.",
        )

    base_dir = get_upload_dir()
    if not base_dir.is_absolute():
        base_dir = get_upload_dir()

    voter_card_dir = base_dir / "training_portal_voter_cards"
    voter_card_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = voter_card_dir / safe_name

    content = await file.read()
    with open(file_path, "wb") as output_file:
        output_file.write(content)

    return {"voter_card_url": f"/uploads/training_portal_voter_cards/{safe_name}"}


def _make_transaction_id() -> str:
    return f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"


def _user_display_name(user: User, fallback: str = "User") -> str:
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if name:
        return name
    email = (user.email or "").strip()
    if email:
        return email.split("@")[0]
    return fallback


def _make_invoice_number(transaction_id: str) -> str:
    return f"INV-{transaction_id}"


async def _batch_student_count(db: AsyncSession, batch_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.batch_id == batch_id,
            TrainingPortalEnrollment.status != "dropped",
        )
    )
    return int(result.scalar() or 0)


def _is_fee_complete(enrollment: TrainingPortalEnrollment) -> bool:
    if enrollment.payment_status in ("paid_online", "paid_offline", "free"):
        return True
    return enrollment.balance_due <= 0.01 and enrollment.paid_amount > 0


def _is_fee_complete_from_create(body: PortalEnrollmentCreate) -> bool:
    if body.payment_status in ("paid_online", "paid_offline", "free"):
        if body.payment_status == "free":
            return True
        return body.balance_due <= 0.01
    return False


async def _try_assign_preferred_batch(
    db: AsyncSession,
    enrollment: TrainingPortalEnrollment,
    *,
    notify: bool = True,
) -> bool:
    preferred_id = getattr(enrollment, "preferred_batch_id", None)
    if not preferred_id or enrollment.batch_id:
        return False
    if not _is_fee_complete(enrollment):
        return False

    batch_result = await db.execute(
        select(TrainingPortalBatch).where(TrainingPortalBatch.id == preferred_id)
    )
    batch = batch_result.scalar_one_or_none()
    if not batch or batch.course_id != enrollment.item_id:
        enrollment.preferred_batch_id = None
        return False

    seats = await _batch_student_count(db, batch.id)
    if seats >= batch.max_seats:
        if notify:
            db.add(
                TrainingPortalCandidateNotification(
                    id=str(uuid.uuid4()),
                    candidate_email=enrollment.candidate_email,
                    notification_type="batch_full",
                    title="Selected batch is full",
                    description=f'Batch "{batch.batch_name}" is full. Please choose another batch or contact admin.',
                    detail="Your fee is recorded. Admin can assign you to an available batch.",
                    event_date=datetime.utcnow().strftime("%Y-%m-%d"),
                    severity="warning",
                )
            )
        return False

    enrollment.batch_id = batch.id
    enrollment.batch_name = batch.batch_name
    enrollment.preferred_batch_id = None
    enrollment.updated_at = datetime.utcnow()

    if notify:
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=enrollment.candidate_email,
                notification_type="batch_assigned",
                title="Batch Assigned",
                description=f'You have been assigned to batch "{batch.batch_name}".',
                detail=f"Schedule: {batch.time_slot}. Venue: {batch.venue}.",
                event_date=datetime.utcnow().strftime("%Y-%m-%d"),
                severity="success",
            )
        )
    return True


async def _sync_batch_enrollments(
    db: AsyncSession,
    batch: TrainingPortalBatch,
    enrollment_ids: list[str],
    background_tasks: BackgroundTasks,
) -> None:
    if len(enrollment_ids) > MAX_BATCH_STUDENTS:
        raise HTTPException(status_code=400, detail=f"Cannot assign more than {MAX_BATCH_STUDENTS} students")

    current_result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.batch_id == batch.id)
    )
    current_rows = list(current_result.scalars().all())
    current_ids = {row.id for row in current_rows}
    target_ids = set(enrollment_ids)

    to_remove = [enrollment for enrollment in current_rows if enrollment.id not in target_ids]
    if to_remove:
        names = ", ".join(enrollment.candidate_name for enrollment in to_remove[:3])
        extra = f" and {len(to_remove) - 3} more" if len(to_remove) > 3 else ""
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot remove enrolled students already assigned to this batch: {names}{extra}. "
                "Reassign them to another batch first if needed."
            ),
        )

    to_add = [eid for eid in enrollment_ids if eid not in current_ids]
    if to_add:
        await _assign_enrollments_to_batch(
            db,
            batch,
            to_add,
            background_tasks,
            notify=True,
        )


async def _record_transaction(
    db: AsyncSession,
    *,
    enrollment: TrainingPortalEnrollment,
    transaction_type: str,
    amount: float,
    payment_mode: Optional[str] = None,
    status: str = "completed",
    provider: Optional[str] = None,
    provider_transaction_id: Optional[str] = None,
    reference_order_id: Optional[str] = None,
    transaction_reference: Optional[str] = None,
    bank_name: Optional[str] = None,
    notes: Optional[str] = None,
    created_by_id: Optional[str] = None,
) -> TrainingPortalTransaction:
    row = TrainingPortalTransaction(
        id=str(uuid.uuid4()),
        transaction_id=_make_transaction_id(),
        enrollment_id=enrollment.id,
        candidate_email=enrollment.candidate_email,
        candidate_name=enrollment.candidate_name,
        program_title=enrollment.title,
        transaction_type=transaction_type,
        amount=amount,
        payment_mode=payment_mode,
        status=status,
        provider=provider,
        provider_transaction_id=provider_transaction_id,
        reference_order_id=reference_order_id,
        transaction_reference=transaction_reference,
        bank_name=bank_name,
        batch_id=enrollment.batch_id,
        batch_name=enrollment.batch_name,
        notes=notes,
        created_by_id=created_by_id,
    )
    db.add(row)
    return row


async def _emi_interest_for_enrollment(
    db: AsyncSession, enrollment: TrainingPortalEnrollment
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Returns (base_fee, interest_amount, interest_percent) when the enrollment's
    total fee exceeds the course's standard fee (i.e. an EMI surcharge applies)."""
    if enrollment.enrollment_type != "course" or not enrollment.item_id:
        return None, None, None
    course_result = await db.execute(
        select(TrainingPortalCourse).where(TrainingPortalCourse.id == enrollment.item_id)
    )
    course = course_result.scalar_one_or_none()
    if not course or not course.fee or course.fee <= 0:
        return None, None, None
    base_fee = float(course.fee)
    interest_amount = round(float(enrollment.total_fee) - base_fee, 2)
    if interest_amount <= 0:
        return base_fee, None, None
    interest_percent = round((interest_amount / base_fee) * 100, 2)
    return base_fee, interest_amount, interest_percent


async def _build_invoice(
    db: AsyncSession,
    transaction: TrainingPortalTransaction,
    enrollment: TrainingPortalEnrollment,
) -> PortalPaymentInvoiceOut:
    base_fee, interest_amount, interest_percent = await _emi_interest_for_enrollment(db, enrollment)
    line_items = [
        PortalInvoiceLineItem(
            label=f"{transaction.program_title} ({transaction.transaction_type.title()})",
            amount=transaction.amount,
        )
    ]
    if interest_amount:
        line_items.append(
            PortalInvoiceLineItem(
                label=f"Includes EMI Interest / Surcharge ({interest_percent}% Interest)",
                amount=interest_amount,
            )
        )

    txn_history_result = await db.execute(
        select(TrainingPortalTransaction)
        .where(TrainingPortalTransaction.enrollment_id == enrollment.id)
        .order_by(TrainingPortalTransaction.created_at.desc())
    )
    transaction_history = [transaction_to_out(row) for row in txn_history_result.scalars().all()]

    return PortalPaymentInvoiceOut(
        invoice_number=_make_invoice_number(transaction.transaction_id),
        transaction_id=transaction.transaction_id,
        transaction_type=transaction.transaction_type,
        invoice_date=transaction.created_at,
        generated_at=datetime.utcnow(),
        candidate_name=transaction.candidate_name,
        candidate_email=transaction.candidate_email,
        candidate_phone=enrollment.candidate_phone,
        program_title=transaction.program_title,
        batch_name=transaction.batch_name or enrollment.batch_name,
        payment_mode=transaction.payment_mode or enrollment.payment_mode,
        provider=transaction.provider,
        provider_transaction_id=transaction.provider_transaction_id,
        reference_order_id=transaction.reference_order_id,
        transaction_reference=transaction.transaction_reference,
        bank_name=transaction.bank_name,
        status=transaction.status,
        currency=transaction.currency,
        amount=transaction.amount,
        total_fee=enrollment.total_fee,
        discount_amount=float(getattr(enrollment, "discount_amount", 0.0) or 0.0),
        paid_amount=enrollment.paid_amount,
        balance_due=enrollment.balance_due,
        enrollment_date=enrollment.enrollment_date,
        notes=transaction.notes or enrollment.notes,
        line_items=line_items,
        base_fee=base_fee,
        emi_interest_amount=interest_amount,
        emi_interest_percent=interest_percent,
        transactions=transaction_history,
    )


async def _assign_enrollments_to_batch(
    db: AsyncSession,
    batch: TrainingPortalBatch,
    enrollment_ids: list[str],
    background_tasks: BackgroundTasks,
    *,
    notify: bool = True,
) -> list[TrainingPortalEnrollment]:
    if not enrollment_ids:
        return []

    current_count = await _batch_student_count(db, batch.id)
    if current_count + len(enrollment_ids) > batch.max_seats:
        raise HTTPException(status_code=400, detail="Batch does not have enough open seats")

    enrollments_result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id.in_(enrollment_ids))
    )
    selected = list(enrollments_result.scalars().all())
    if len(selected) != len(enrollment_ids):
        raise HTTPException(status_code=400, detail="One or more enrollments not found")

    assigned: list[TrainingPortalEnrollment] = []
    for enrollment in selected:
        if enrollment.enrollment_type != "course" or enrollment.item_id != batch.course_id:
            raise HTTPException(status_code=400, detail="All students must be enrolled in the batch course")
        if not _is_fee_complete(enrollment):
            raise HTTPException(
                status_code=400,
                detail=f"Student {enrollment.candidate_email} has not completed fee payment",
            )
        if enrollment.batch_id and enrollment.batch_id != batch.id:
            raise HTTPException(
                status_code=400,
                detail=f"Student {enrollment.candidate_email} is already assigned to another batch",
            )
        if enrollment.batch_id == batch.id:
            continue
        enrollment.batch_id = batch.id
        enrollment.batch_name = batch.batch_name
        enrollment.preferred_batch_id = None
        enrollment.updated_at = datetime.utcnow()
        assigned.append(enrollment)

        if notify:
            notif = TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=enrollment.candidate_email,
                notification_type="batch_assigned",
                title="Batch Assigned",
                description=f'You have been assigned to batch "{batch.batch_name}".',
                detail=f"Schedule: {batch.time_slot}. Venue: {batch.venue}.",
                event_date=datetime.utcnow().strftime("%Y-%m-%d"),
                severity="success",
            )
            db.add(notif)
            background_tasks.add_task(
                send_training_portal_batch_assigned_email,
                enrollment.candidate_email,
                enrollment.candidate_name,
                enrollment.title,
                batch.batch_name,
                batch.time_slot,
                batch.venue,
                batch.days,
            )

    await db.commit()
    return assigned


async def _enrollment_has_scheduled_classes(db: AsyncSession, enrollment: TrainingPortalEnrollment) -> bool:
    if enrollment.batch_id:
        result = await db.execute(
            select(func.count()).select_from(TrainingPortalClassSession).where(
                TrainingPortalClassSession.batch_id == enrollment.batch_id
            )
        )
        return int(result.scalar() or 0) > 0
    return False


async def _is_refund_request_eligible(db: AsyncSession, enrollment: TrainingPortalEnrollment) -> tuple[bool, str]:
    if enrollment.paid_amount <= 0:
        return False, "No payment to refund"
    if await _enrollment_has_scheduled_classes(db, enrollment):
        return False, "Classes have already been scheduled for your batch"
    try:
        enrolled_on = datetime.strptime(enrollment.enrollment_date, "%Y-%m-%d")
    except ValueError:
        enrolled_on = enrollment.created_at
    if datetime.utcnow() < enrolled_on + timedelta(days=REFUND_REQUEST_MIN_DAYS):
        return False, f"Refund requests are available after {REFUND_REQUEST_MIN_DAYS} days of enrollment"
    pending = await db.execute(
        select(TrainingPortalRefundRequest).where(
            TrainingPortalRefundRequest.enrollment_id == enrollment.id,
            TrainingPortalRefundRequest.status == "pending",
        )
    )
    if pending.scalar_one_or_none():
        return False, "A refund request is already pending review"
    return True, "Eligible"


async def _get_or_create_payment_settings(db: AsyncSession) -> TrainingPortalPaymentSettings:
    result = await db.execute(
        select(TrainingPortalPaymentSettings).where(TrainingPortalPaymentSettings.id == "default")
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = TrainingPortalPaymentSettings(id="default")
    db.add(row)
    await db.commit()
    return row


async def _notify_admins(
    db: AsyncSession,
    notification_type: str,
    title: str,
    description: str,
    detail: Optional[str] = None,
    severity: str = "info",
) -> None:
    admin_result = await db.execute(
        select(User.email).where(User.is_super_admin.is_(True))
    )
    admin_emails = admin_result.scalars().all()
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    for email in admin_emails:
        if email:
            db.add(
                TrainingPortalCandidateNotification(
                    id=str(uuid.uuid4()),
                    candidate_email=email.strip().lower(),
                    recipient_role="admin",
                    notification_type=notification_type,
                    title=title,
                    description=description,
                    detail=detail,
                    event_date=today_str,
                    severity=severity,
                )
            )


async def _refresh_internship_seats(db: AsyncSession, internship_id: str) -> None:
    result = await db.execute(
        select(TrainingPortalInternship).where(TrainingPortalInternship.id == internship_id)
    )
    internship = result.scalar_one_or_none()
    if not internship:
        return
    count_result = await db.execute(
        select(func.count()).select_from(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.enrollment_type == "internship",
            TrainingPortalEnrollment.item_id == internship_id,
            TrainingPortalEnrollment.status != "dropped",
        )
    )
    internship.seats_filled = int(count_result.scalar() or 0)
    internship.updated_at = datetime.utcnow()


async def _mark_enrollment_paid(
    db: AsyncSession,
    enrollment: TrainingPortalEnrollment,
    paid_amount: float,
    payment_mode: str = "online",
    *,
    provider: Optional[str] = "razorpay",
    provider_transaction_id: Optional[str] = None,
    reference_order_id: Optional[str] = None,
    created_by_id: Optional[str] = None,
) -> None:
    old_status = enrollment.status
    enrollment.paid_amount = round((enrollment.paid_amount or 0.0) + paid_amount, 2)
    enrollment.balance_due = max(0.0, round(enrollment.total_fee - enrollment.paid_amount, 2))
    if enrollment.balance_due > 0.01:
        enrollment.payment_status = "partially_paid"
    else:
        enrollment.payment_status = "paid_online" if payment_mode == "online" else "paid_offline"
    enrollment.payment_mode = payment_mode
    enrollment.status = "active"
    enrollment.updated_at = datetime.utcnow()
    await _try_assign_preferred_batch(db, enrollment)
    await _record_transaction(
        db,
        enrollment=enrollment,
        transaction_type="payment",
        amount=paid_amount,
        payment_mode=payment_mode,
        provider=provider,
        provider_transaction_id=provider_transaction_id,
        reference_order_id=reference_order_id,
        notes="Online payment captured" if payment_mode == "online" else "Offline payment recorded",
        created_by_id=created_by_id,
    )

    today = datetime.utcnow().strftime("%Y-%m-%d")
    db.add(
        TrainingPortalCandidateNotification(
            id=str(uuid.uuid4()),
            candidate_email=enrollment.candidate_email.strip().lower(),
            recipient_role="candidate",
            notification_type="payment_confirmed",
            title="Payment Confirmed",
            description=f"Your payment of ₹{paid_amount:,.2f} for {enrollment.title} was confirmed.",
            detail=f"Payment Mode: {payment_mode.title()}. Transaction ID: {provider_transaction_id or 'N/A'}.",
            event_date=today,
            severity="success",
        )
    )

    if old_status != "active":
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=enrollment.candidate_email.strip().lower(),
                recipient_role="candidate",
                notification_type="enrollment_confirmed",
                title="Enrollment Confirmed",
                description=f"Welcome! Your enrollment in {enrollment.title} is now active.",
                detail="Please choose a batch from your dashboard if you haven't already.",
                event_date=today,
                severity="success",
            )
        )



# ── Payment settings ──────────────────────────────────────────────────────────

@router.get("/payment-settings", response_model=PortalPaymentSettingsOut)
async def get_payment_settings(
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_create_payment_settings(db)
    return payment_settings_to_out(row)


@router.put("/payment-settings", response_model=PortalPaymentSettingsOut)
async def update_payment_settings(
    body: PortalPaymentSettingsUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_create_payment_settings(db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.updated_at = datetime.utcnow()
    await db.commit()
    return payment_settings_to_out(row)


# ── Dashboard summary ─────────────────────────────────────────────────────────

@router.get("/dashboard-summary", response_model=PortalDashboardSummaryOut)
async def get_dashboard_summary(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD enrollment/payment range start"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD enrollment/payment range end"),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated admin KPIs, fee charts, and teacher workload from live DB data."""
    data = await build_dashboard_summary(db, date_from=date_from, date_to=date_to)
    return PortalDashboardSummaryOut(**data)


# ── Enrollments ───────────────────────────────────────────────────────────────

@router.get("/enrollments", response_model=List[PortalEnrollmentOut])
async def list_enrollments(
    response: Response,
    candidate_email: Optional[str] = Query(None),
    enrollment_type: Optional[str] = Query(None, alias="type"),
    course_id: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    unassigned_only: bool = Query(False),
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1, le=100),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalEnrollment).order_by(TrainingPortalEnrollment.created_at.desc())
    is_admin = getattr(current_user, "is_super_admin", False)
    user_role = getattr(current_user, "role", None)

    if is_admin:
        if candidate_email:
            query = query.where(TrainingPortalEnrollment.candidate_email == candidate_email.strip().lower())
    elif user_role == "teacher":
        teacher_batch_ids = await _teacher_batch_ids_for_user(db, current_user)
        if batch_id:
            if batch_id not in teacher_batch_ids:
                return []
            query = query.where(TrainingPortalEnrollment.batch_id == batch_id)
        elif teacher_batch_ids:
            query = query.where(TrainingPortalEnrollment.batch_id.in_(teacher_batch_ids))
        else:
            return []
    else:
        email = (current_user.email or "").strip().lower()
        query = query.where(TrainingPortalEnrollment.candidate_email == email)

    if enrollment_type:
        query = query.where(TrainingPortalEnrollment.enrollment_type == enrollment_type)
    if course_id:
        query = query.where(
            TrainingPortalEnrollment.enrollment_type == "course",
            TrainingPortalEnrollment.item_id == course_id,
        )
    if batch_id:
        query = query.where(TrainingPortalEnrollment.batch_id == batch_id)
    if unassigned_only:
        query = query.where(
            TrainingPortalEnrollment.enrollment_type == "course",
            TrainingPortalEnrollment.batch_id.is_(None),
        )

    # Count total matching rows before pagination is applied
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar() or 0
    response.headers["X-Total-Count"] = str(total_count)

    effective_limit = limit or page_size
    if page is not None and effective_limit is not None:
        offset = (page - 1) * effective_limit
        query = query.offset(offset).limit(effective_limit)

    result = await db.execute(query)
    enrollment_rows = result.scalars().all()
    for e in enrollment_rows:
        total_att = await db.execute(
            select(func.count()).select_from(TrainingPortalAttendanceRecord).where(
                TrainingPortalAttendanceRecord.enrollment_id == e.id
            )
        )
        t_marked = int(total_att.scalar() or 0)
        if t_marked == 0 and e.candidate_email:
            total_att = await db.execute(
                select(func.count()).select_from(TrainingPortalAttendanceRecord).where(
                    func.lower(TrainingPortalAttendanceRecord.candidate_email) == e.candidate_email.strip().lower()
                )
            )
            t_marked = int(total_att.scalar() or 0)

        if t_marked > 0:
            email_clean = (e.candidate_email or "").strip().lower()
            present_att = await db.execute(
                select(func.count()).select_from(TrainingPortalAttendanceRecord).where(
                    func.lower(TrainingPortalAttendanceRecord.candidate_email) == email_clean,
                    TrainingPortalAttendanceRecord.status.in_(["present", "late", "on_leave"]),
                )
            )
            p_count = int(present_att.scalar() or 0)
            e.attendance_percentage = round((p_count / t_marked) * 100)

    return [enrollment_to_out(row) for row in enrollment_rows]


@router.post("/enrollments/export-csv")
async def export_students_csv(
    body: dict = {},
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    emails = body.get("emails")
    
    # Fetch all enrollments
    query = select(TrainingPortalEnrollment)
    res_en = await db.execute(query)
    db_enrollments = res_en.scalars().all()
    
    # Fetch all leave requests
    res_lv = await db.execute(select(TrainingPortalLeaveRequest))
    db_leaves = res_lv.scalars().all()
    
    # Group enrollments by candidate_email
    by_email = {}
    for e in db_enrollments:
        by_email.setdefault(e.candidate_email, []).append(e)
        
    # Group leave requests by candidate_email
    leaves_by_email = {}
    for l in db_leaves:
        leaves_by_email.setdefault(l.candidate_email, []).append(l)
        
    # Build directory entries
    targets = []
    for email, st_enrollments in by_email.items():
        if emails is not None and email not in emails:
            continue
            
        active = [e for e in st_enrollments if e.status == "active"]
        total_fee = sum(e.total_fee for e in st_enrollments)
        total_paid = sum(e.paid_amount for e in st_enrollments)
        total_balance_due = sum(e.balance_due for e in st_enrollments)
        
        avg_attendance = 0
        if len(st_enrollments) > 0:
            avg_attendance = round(sum(e.attendance_percentage for e in st_enrollments) / len(st_enrollments))
            
        primary_status = "completed"
        if len(active) > 0:
            primary_status = "active"
        elif any(e.status == "pending" for e in st_enrollments):
            primary_status = "pending"
        elif any(e.status == "dropped" for e in st_enrollments):
            primary_status = "dropped"
            
        has_confirmed_course = any(
            e.enrollment_type == "course" and e.status not in ("pending", "dropped")
            for e in st_enrollments
        )
        
        phone = st_enrollments[0].candidate_phone
        name = st_enrollments[0].candidate_name
        
        local_part = email.split('@')[0].upper() if '@' in email else "UNKNOWN"
        student_code = f"STU-{local_part}"
        
        st_leaves = leaves_by_email.get(email, [])
        pending_slips = len([l for l in st_leaves if l.status == "Pending"])
        
        laptop_confirmed = any(bool(getattr(e, "laptop_confirmed", False)) for e in st_enrollments)
        
        targets.append({
            "name": name,
            "studentCode": student_code,
            "email": email,
            "phone": phone or "",
            "laptopConfirmed": "Yes" if laptop_confirmed else "No",
            "avgAttendance": avg_attendance,
            "status": primary_status,
            "enrolledBatchesCount": len([e for e in st_enrollments if e.batch_id or e.enrollment_type == "internship"]),
            "pendingAbsenceSlips": pending_slips,
        })
        
    targets.sort(key=lambda x: x["name"])
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Student Name',
        'Student Code',
        'Email',
        'Phone',
        'Laptop Confirmed',
        'Avg Attendance (%)',
        'Status',
        'Enrolled Batches Count',
        'Pending Absence Slips',
    ])
    
    for t in targets:
        writer.writerow([
            t["name"],
            t["studentCode"],
            t["email"],
            t["phone"],
            t["laptopConfirmed"],
            t["avgAttendance"],
            t["status"],
            t["enrolledBatchesCount"],
            t["pendingAbsenceSlips"],
        ])
        
    csv_data = output.getvalue()
    output.close()
    
    return StreamingResponse(
        io.BytesIO(csv_data.encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=students_export_{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
        }
    )


@router.post("/enrollments/send-reminder")
async def send_reminder_to_students(
    body: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    emails = body.get("emails")
    if not emails:
        raise HTTPException(status_code=400, detail="No emails provided")
        
    result = await db.execute(
        select(TrainingPortalEnrollment.candidate_email, TrainingPortalEnrollment.candidate_name)
        .where(TrainingPortalEnrollment.candidate_email.in_(emails))
    )
    email_to_name = {row[0]: row[1] for row in result.all()}
    
    for email in emails:
        name = email_to_name.get(email, "Trainee")
        
        notif = TrainingPortalCandidateNotification(
            id=str(uuid.uuid4()),
            candidate_email=email,
            notification_type="admin_reminder",
            title="Training Portal Reminder",
            description="You have a new reminder from the portal administrator. Please check your dashboard or email for updates.",
            event_date=datetime.utcnow().strftime("%Y-%m-%d"),
            severity="info",
        )
        db.add(notif)
        
        background_tasks.add_task(
            send_notification_email,
            email,
            name,
            "Admin Training Reminder",
            "This is a reminder from the training portal administrator. Please log in to your training portal dashboard to view updates or contact the administration if you have questions."
        )
        
    await db.commit()
    return {"status": "ok", "message": f"Reminders queued for {len(emails)} student(s)."}


@router.post("/enrollments/bulk-delete")
async def bulk_delete_students(
    body: dict,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    emails = body.get("emails")
    if not emails:
        raise HTTPException(status_code=400, detail="No emails provided")
        
    # Get enrollment IDs to clean up transactions
    res_en = await db.execute(
        select(TrainingPortalEnrollment.id).where(TrainingPortalEnrollment.candidate_email.in_(emails))
    )
    enrollment_ids = [row[0] for row in res_en.all()]
    if not enrollment_ids:
        raise HTTPException(status_code=404, detail="No matching student records found to delete.")
    await db.execute(
        delete(TrainingPortalTransaction).where(TrainingPortalTransaction.enrollment_id.in_(enrollment_ids))
    )

    # Delete enrollments
    await db.execute(
        delete(TrainingPortalEnrollment).where(TrainingPortalEnrollment.candidate_email.in_(emails))
    )
    # Delete leave requests
    await db.execute(
        delete(TrainingPortalLeaveRequest).where(TrainingPortalLeaveRequest.candidate_email.in_(emails))
    )
    # Delete behavior reports
    await db.execute(
        delete(TrainingPortalBehaviorReport).where(TrainingPortalBehaviorReport.candidate_email.in_(emails))
    )
    # Delete notifications
    await db.execute(
        delete(TrainingPortalCandidateNotification).where(TrainingPortalCandidateNotification.candidate_email.in_(emails))
    )
    
    await db.commit()
    return {"status": "ok", "message": f"Successfully deleted records for {len(emails)} student(s)."}


def _calculate_duration_minutes(start_str: str, end_str: str) -> str:
    if not start_str or not end_str:
        return "—"
    try:
        s_val = start_str.strip().upper()
        e_val = end_str.strip().upper()
        
        from datetime import datetime
        formats = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"]
        t_start, t_end = None, None
        for fmt in formats:
            if not t_start:
                try:
                    t_start = datetime.strptime(s_val, fmt)
                except ValueError:
                    pass
            if not t_end:
                try:
                    t_end = datetime.strptime(e_val, fmt)
                except ValueError:
                    pass
        if t_start and t_end:
            diff = t_end - t_start
            minutes = int(diff.total_seconds() / 60)
            if minutes < 0:
                minutes += 24 * 60
            return f"{minutes} mins"
    except Exception:
        pass
    return "—"


@router.post("/export-csv")
async def generic_export_csv(
    body: dict,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    entity = body.get("entity")
    ids = body.get("ids")
    
    if not entity:
        raise HTTPException(status_code=400, detail="Entity type is required")
        
    output = io.StringIO()
    writer = csv.writer(output)
    filename = f"{entity}_export_{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
    
    if entity == "batches":
        query = select(TrainingPortalBatch).order_by(TrainingPortalBatch.created_at.desc())
        if ids:
            query = query.where(TrainingPortalBatch.id.in_(ids))
        res = await db.execute(query)
        batches = res.scalars().all()

        courses_res = await db.execute(select(TrainingPortalCourse))
        courses_map = {c.id: c for c in courses_res.scalars().all()}

        batch_ids = [b.id for b in batches]
        sessions_by_batch: dict[str, list[TrainingPortalClassSession]] = defaultdict(list)
        if batch_ids:
            session_rows = (
                await db.execute(
                    select(TrainingPortalClassSession).where(TrainingPortalClassSession.batch_id.in_(batch_ids))
                )
            ).scalars().all()
            for session in session_rows:
                sessions_by_batch[session.batch_id].append(session)

        writer.writerow([
            'Batch Name', 'Course Title', 'Instructor', 'Schedule', 'Days', 'Venue',
            'Max Seats', 'Class Mode', 'Status'
        ])
        for b in batches:
            course = courses_map.get(b.course_id)
            days_str, schedule_time = _batch_export_schedule(b, sessions_by_batch.get(b.id, []))
            status_label = _batch_export_status(b, len(sessions_by_batch.get(b.id, [])))
            class_mode = b.delivery_mode or (course.delivery_mode if course else None) or '-'
            course_title = course.title if course else 'Unknown Course'
            writer.writerow([
                b.batch_name,
                course_title,
                b.instructor_name or '-',
                schedule_time or '-',
                days_str or '-',
                b.venue or '-',
                b.max_seats,
                class_mode,
                status_label,
            ])

    elif entity == "ledger":
        query = select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.enrollment_type == "course")
        if ids:
            query = query.where(or_(
                TrainingPortalEnrollment.id.in_(ids),
                TrainingPortalEnrollment.candidate_email.in_(ids)
            ))
        res = await db.execute(query)
        enrollments = res.scalars().all()
        
        writer.writerow([
            'Student Name', 'Email', 'Course/Program', 'Payment Type', 'Total Fee',
            'Paid Amount', 'Balance Due', 'Payment Status'
        ])
        for e in enrollments:
            writer.writerow([
                e.candidate_name, e.candidate_email, e.title, e.payment_type,
                e.total_fee, e.paid_amount, e.balance_due, e.payment_status
            ])
            
    elif entity == "transactions":
        query = select(TrainingPortalTransaction).order_by(TrainingPortalTransaction.created_at.desc())
        if ids:
            query = query.where(TrainingPortalTransaction.id.in_(ids))
        res = await db.execute(query)
        txns = res.scalars().all()
        
        writer.writerow([
            'Transaction ID', 'Date', 'Student Name', 'Email', 'Program',
            'Type', 'Amount', 'Payment Mode', 'Status', 'Notes'
        ])
        for t in txns:
            date_str = t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "—"
            writer.writerow([
                t.transaction_id, date_str, t.candidate_name, t.candidate_email, t.program_title,
                t.transaction_type, t.amount, t.payment_mode or "—", t.status, t.notes or ""
            ])
            
    elif entity == "attendance":
        is_admin = getattr(current_user, "is_super_admin", False)
        user_role = getattr(current_user, "role", None)
        
        teacher_batch_ids = None
        if user_role == "teacher" and not is_admin:
            teacher_batch_ids = await _teacher_batch_ids_for_user(db, current_user)
            if not teacher_batch_ids:
                writer.writerow([
                    'Trainee Name', 'Email', 'Batch Name', 'Session Title', 'Date', 'Status', 'Duration'
                ])
                csv_data = output.getvalue()
                output.close()
                return StreamingResponse(
                    io.BytesIO(csv_data.encode("utf-8")),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )

        query = (
            select(
                TrainingPortalAttendanceRecord,
                TrainingPortalClassSession,
                TrainingPortalBatch.batch_name
            )
            .join(
                TrainingPortalClassSession,
                TrainingPortalAttendanceRecord.class_session_id == TrainingPortalClassSession.id,
            )
            .outerjoin(
                TrainingPortalBatch,
                TrainingPortalAttendanceRecord.batch_id == TrainingPortalBatch.id,
            )
            .order_by(TrainingPortalAttendanceRecord.marked_at.desc())
        )
        if ids:
            query = query.where(TrainingPortalAttendanceRecord.id.in_(ids))

        if teacher_batch_ids is not None:
            query = query.where(TrainingPortalAttendanceRecord.batch_id.in_(teacher_batch_ids))

        is_student = not is_admin and teacher_batch_ids is None
        if is_student:
            user_email = (current_user.email or "").lower()
            query = query.where(TrainingPortalAttendanceRecord.candidate_email == user_email)

        res = await db.execute(query)
        rows = res.all()

        writer.writerow([
            'Trainee Name', 'Email', 'Batch Name', 'Session Title', 'Date', 'Status', 'Duration'
        ])
        for record, session, batch_name in rows:
            session_date = record.occurrence_date or session.date
            duration = _calculate_duration_minutes(session.start_time, session.end_time)
            writer.writerow([
                record.candidate_name,
                record.candidate_email,
                batch_name or "—",
                session.title or "—",
                session_date,
                record.status.replace("_", " ").title(),
                duration
            ])
            
    elif entity == "leaves":
        query = select(TrainingPortalLeaveRequest).order_by(TrainingPortalLeaveRequest.created_at.desc())
        if ids:
            query = query.where(TrainingPortalLeaveRequest.id.in_(ids))
        res = await db.execute(query)
        leaves = res.scalars().all()
        
        writer.writerow([
            'Requester Name', 'Email', 'Date', 'Status', 'Reason', 'Reviewed By'
        ])
        for l in leaves:
            requester = l.candidate_name or l.teacher_name or "Unknown"
            email = l.candidate_email or l.teacher_email or "—"
            writer.writerow([
                requester, email, l.date, l.status, l.reason, l.reviewed_by_id or "—"
            ])
            
    elif entity == "certificates":
        query = select(TrainingPortalEnrollment)
        if ids:
            query = query.where(TrainingPortalEnrollment.id.in_(ids))
        else:
            query = query.where(TrainingPortalEnrollment.status.in_(["active", "completed"]))
        res = await db.execute(query)
        enrollments = res.scalars().all()
        
        writer.writerow([
            'Recipient Name', 'Email', 'Course Title', 'Issue Date', 'Certificate ID', 'Status'
        ])
        for e in enrollments:
            issue_date = e.updated_at.strftime("%Y-%m-%d") if (e.is_certificate_issued and e.updated_at) else "—"
            status = e.certificate_status or ("Issued" if e.is_certificate_issued else "Pending")
            writer.writerow([
                e.candidate_name, e.candidate_email, e.title, issue_date, e.certificate_id or "—", status
            ])
            
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")
        
    csv_data = output.getvalue()
    output.close()
    
    return StreamingResponse(
        io.BytesIO(csv_data.encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/enrollments", response_model=PortalEnrollmentOut, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    body: PortalEnrollmentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    email = (body.candidate_email or current_user.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Candidate email is required")

    name = body.candidate_name or f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or email.split("@")[0]
    phone = body.candidate_phone or current_user.phone

    # Delete any stale initiated enrollments that never completed payment.
    # For course enrollments, keep separate batch registrations distinct so the
    # same student can join more than one class for the same course.
    initiated_filters = [
        TrainingPortalEnrollment.candidate_email == email,
        TrainingPortalEnrollment.enrollment_type == body.enrollment_type,
        TrainingPortalEnrollment.status == "payment_initiated",
    ]
    if body.enrollment_type == "course" and body.batch_id:
        initiated_filters.extend([
            TrainingPortalEnrollment.item_id == body.item_id,
            TrainingPortalEnrollment.batch_id == body.batch_id,
        ])
    else:
        initiated_filters.append(TrainingPortalEnrollment.item_id == body.item_id)
    await db.execute(delete(TrainingPortalEnrollment).where(*initiated_filters))
    await db.commit()

    duplicate_filters = [
        TrainingPortalEnrollment.candidate_email == email,
        TrainingPortalEnrollment.enrollment_type == body.enrollment_type,
        TrainingPortalEnrollment.status != "dropped",
    ]
    if body.enrollment_type == "course" and body.batch_id:
        duplicate_filters.extend([
            TrainingPortalEnrollment.item_id == body.item_id,
            TrainingPortalEnrollment.batch_id == body.batch_id,
        ])
    else:
        duplicate_filters.append(TrainingPortalEnrollment.item_id == body.item_id)
    dup = await db.execute(select(TrainingPortalEnrollment).where(*duplicate_filters))
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already enrolled in this program")

    if body.enrollment_type == "internship":
        internship_result = await db.execute(
            select(TrainingPortalInternship).where(TrainingPortalInternship.id == body.item_id)
        )
        internship = internship_result.scalar_one_or_none()
        if not internship or internship.status != "active":
            raise HTTPException(status_code=400, detail="Internship is not available")
        if internship.seats_filled >= internship.max_seats:
            raise HTTPException(status_code=400, detail="Internship cohort is full")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    batch_name: Optional[str] = None
    batch_id: Optional[str] = None
    preferred_batch_id: Optional[str] = None

    if body.batch_id and body.enrollment_type == "course":
        batch_result = await db.execute(
            select(TrainingPortalBatch).where(TrainingPortalBatch.id == body.batch_id)
        )
        batch = batch_result.scalar_one_or_none()
        if not batch or batch.course_id != body.item_id:
            raise HTTPException(status_code=400, detail="Invalid batch for this course")
        if batch.status not in ("upcoming", "ongoing"):
            raise HTTPException(status_code=400, detail="Selected batch is not open for enrollment")

        # A token booking reserves the seat immediately, same as a fully-paid
        # enrollment — the whole point of the token payment is to lock the seat
        # even though the remaining balance is still outstanding.
        if _is_fee_complete_from_create(body) or body.payment_status == "token_paid":
            seats = await _batch_student_count(db, batch.id)
            if seats >= batch.max_seats:
                raise HTTPException(status_code=400, detail="Selected batch is full")
            batch_id = batch.id
            batch_name = batch.batch_name
        else:
            preferred_batch_id = batch.id

    enrollment = TrainingPortalEnrollment(
        id=str(uuid.uuid4()),
        candidate_user_id=current_user.id,
        candidate_name=name,
        candidate_email=email,
        candidate_phone=phone,
        enrollment_type=body.enrollment_type,
        item_id=body.item_id,
        batch_id=batch_id,
        batch_name=batch_name,
        preferred_batch_id=preferred_batch_id,
        title=body.title,
        enrollment_date=today,
        payment_type=body.payment_type,
        payment_status=body.payment_status,
        payment_mode=body.payment_mode,
        total_fee=body.total_fee,
        paid_amount=body.paid_amount,
        balance_due=body.balance_due,
        installments=body.installments,
        voter_card_url=body.voter_card_url,
        laptop_confirmed=bool(getattr(body, "laptop_confirmed", False)),
        notes=body.notes,
        status=(
            "payment_initiated" if body.payment_status == "initiated"
            else "token_booked" if body.payment_status == "token_paid"
            else "active" if body.payment_status in ("paid_online", "paid_offline", "free")
            else "pending"
        ),
    )
    db.add(enrollment)
    await db.commit()

    if batch_id:
        notif = TrainingPortalCandidateNotification(
            id=str(uuid.uuid4()),
            candidate_email=email,
            notification_type="batch_assigned",
            title="Batch Selected",
            description=f'You enrolled in batch "{batch_name}".',
            detail="Class schedule will begin once the batch reaches the minimum student count.",
            event_date=today,
            severity="success",
        )
        db.add(notif)
    elif preferred_batch_id:
        pref_batch_result = await db.execute(
            select(TrainingPortalBatch).where(TrainingPortalBatch.id == preferred_batch_id)
        )
        pref_batch = pref_batch_result.scalar_one_or_none()
        pref_name = pref_batch.batch_name if pref_batch else "your selected batch"
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=email,
                notification_type="batch_pending",
                title="Batch preference saved",
                description=f'You selected batch "{pref_name}".',
                detail="You will be added to this batch once your fee payment is completed and a seat is available.",
                event_date=today,
                severity="info",
            )
        )

    if enrollment.status != "payment_initiated":
        await _notify_admins(
            db=db,
            notification_type="new_enrollment",
            title="New Enrollment Registered",
            description=f"{name} registered for {body.title}.",
            detail=f"Status: {enrollment.status}. Payment Type: {body.payment_type}.",
            severity="info",
        )
        if enrollment.status == "active":
            db.add(
                TrainingPortalCandidateNotification(
                    id=str(uuid.uuid4()),
                    candidate_email=email,
                    recipient_role="candidate",
                    notification_type="enrollment_confirmed",
                    title="Enrollment Confirmed",
                    description=f"Welcome! Your enrollment in {body.title} is now active.",
                    detail="Please choose a batch from your dashboard if you haven't already.",
                    event_date=today,
                    severity="success",
                )
            )

    if body.enrollment_type == "internship":
        await _refresh_internship_seats(db, body.item_id)

    if body.payment_method_route == "email" and body.balance_due > 0:
        background_tasks.add_task(
            send_training_portal_payment_link_email,
            email,
            name,
            body.title,
            body.balance_due,
            enrollment.id,
        )

    return enrollment_to_out(enrollment)


@router.post("/enrollments/{enrollment_id}/confirm-visit", response_model=PortalEnrollmentOut)
async def confirm_venue_visit(
    enrollment_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """SuperAdmin confirms the candidate visited the venue within the 5-day window,
    converting a token-booked seat into a fully confirmed enrollment."""
    result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enrollment.status != "token_booked":
        raise HTTPException(status_code=400, detail="Enrollment is not a pending token booking")
    if enrollment.token_expired:
        raise HTTPException(status_code=400, detail="This booking has already expired due to non-appearance")

    enrollment.status = "active"
    enrollment.updated_at = datetime.utcnow()
    db.add(
        TrainingPortalCandidateNotification(
            id=str(uuid.uuid4()),
            candidate_email=enrollment.candidate_email,
            recipient_role="candidate",
            notification_type="enrollment_confirmed",
            title="Enrollment Confirmed",
            description=f"Welcome! Your enrollment in {enrollment.title} is now active.",
            detail=f"Batch: {enrollment.batch_name or 'To be confirmed'}. Remaining balance: ₹{enrollment.balance_due:,.2f}.",
            event_date=datetime.utcnow().strftime("%Y-%m-%d"),
            severity="success",
        )
    )
    await db.commit()
    return enrollment_to_out(enrollment)


@router.put("/enrollments/{enrollment_id}", response_model=PortalEnrollmentOut)
async def update_enrollment(
    enrollment_id: str,
    body: PortalEnrollmentUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if body.batch_id is not None:
        enrollment.batch_id = body.batch_id or None
    if body.batch_name is not None:
        enrollment.batch_name = body.batch_name
    if body.payment_status is not None:
        enrollment.payment_status = body.payment_status
    if body.payment_mode is not None:
        enrollment.payment_mode = body.payment_mode
    if body.paid_amount is not None:
        enrollment.paid_amount = body.paid_amount
    if body.balance_due is not None:
        enrollment.balance_due = body.balance_due
    if body.voter_card_url is not None:
        enrollment.voter_card_url = body.voter_card_url
    if body.laptop_confirmed is not None:
        enrollment.laptop_confirmed = body.laptop_confirmed
    if body.notes is not None:
        enrollment.notes = body.notes
    if body.status is not None:
        enrollment.status = body.status
    if body.attendance_percentage is not None:
        enrollment.attendance_percentage = body.attendance_percentage
    if body.completion_percentage is not None:
        enrollment.completion_percentage = body.completion_percentage
    if body.is_certificate_issued is not None:
        enrollment.is_certificate_issued = body.is_certificate_issued

    enrollment.updated_at = datetime.utcnow()
    await db.commit()
    return enrollment_to_out(enrollment)


@router.post("/enrollments/record-offline-payment", response_model=PortalEnrollmentOut)
async def record_offline_payment(
    body: PortalOfflinePaymentRecord,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == body.enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    discount_amt = max(0.0, float(body.discount_amount or 0.0))
    if discount_amt > 0:
        current_discount = float(getattr(enrollment, "discount_amount", 0.0) or 0.0)
        enrollment.discount_amount = current_discount + discount_amt

    total_discount = float(getattr(enrollment, "discount_amount", 0.0) or 0.0)
    effective_total_fee = max(0.0, float(enrollment.total_fee or 0.0) - total_discount)

    payment_amt = max(0.0, float(body.amount or 0.0))
    if payment_amt <= 0 and (enrollment.balance_due or 0.0) > 0:
        payment_amt = max(0.0, effective_total_fee - float(enrollment.paid_amount or 0.0))

    new_paid_amount = min(effective_total_fee, float(enrollment.paid_amount or 0.0) + payment_amt)
    new_balance_due = max(0.0, effective_total_fee - new_paid_amount)

    enrollment.paid_amount = new_paid_amount
    enrollment.balance_due = new_balance_due
    enrollment.payment_status = "paid_offline" if new_balance_due <= 0.01 else "partially_paid"
    enrollment.payment_mode = body.payment_mode
    default_notes = f"Offline payment recorded by Admin (Discount: ₹{discount_amt:.2f})" if discount_amt > 0 else "Offline payment recorded by Admin"
    enrollment.notes = body.notes or enrollment.notes or default_notes
    enrollment.status = "active"
    enrollment.updated_at = datetime.utcnow()

    # Update EMI installments list if present
    installments_list = enrollment.installments or []
    if installments_list and isinstance(installments_list, list):
        updated_installments = []
        payment_date_str = body.date or datetime.utcnow().strftime("%Y-%m-%d")
        matched = False

        for inst in installments_list:
            if isinstance(inst, dict):
                inst_copy = dict(inst)
                if not matched and inst_copy.get("status") != "paid":
                    if body.installment_number:
                        if inst_copy.get("number") == body.installment_number:
                            inst_copy["status"] = "paid"
                            inst_copy["paidDate"] = payment_date_str
                            inst_copy["paymentMode"] = body.payment_mode
                            matched = True
                    else:
                        inst_copy["status"] = "paid"
                        inst_copy["paidDate"] = payment_date_str
                        inst_copy["paymentMode"] = body.payment_mode
                        matched = True
                updated_installments.append(inst_copy)
            else:
                updated_installments.append(inst)
        enrollment.installments = updated_installments

    await _try_assign_preferred_batch(db, enrollment)
    await _record_transaction(
        db,
        enrollment=enrollment,
        transaction_type="payment",
        amount=payment_amt,
        payment_mode=body.payment_mode,
        provider="offline",
        transaction_reference=body.transaction_reference,
        bank_name=body.bank_name,
        notes=body.notes or default_notes,
        created_by_id=current_user.id,
    )
    await db.commit()

    # Dispatch formal payment receipt email with attachment to student
    try:
        receipt_no = f"REC-{str(enrollment.id)[:8].upper()}"
        payment_date_str = body.date or datetime.utcnow().strftime("%Y-%m-%d")
        base_fee, _interest_amt, _interest_pct = await _emi_interest_for_enrollment(db, enrollment)
        import asyncio
        asyncio.create_task(
            send_training_enrollment_receipt_email(
                to_email=enrollment.candidate_email,
                first_name=(enrollment.candidate_name or "").split(" ")[0] or enrollment.candidate_name,
                program_title=enrollment.title,
                total_fee=float(enrollment.total_fee or 0.0),
                discount_amount=total_discount,
                paid_amount=float(enrollment.paid_amount or 0.0),
                balance_due=float(enrollment.balance_due or 0.0),
                payment_type=enrollment.payment_type or "Full Payment",
                payment_mode=body.payment_mode,
                receipt_number=receipt_no,
                enrollment_date=payment_date_str,
                batch_name=enrollment.batch_name,
                installments=enrollment.installments,
                base_fee=base_fee,
            )
        )
    except Exception as exc:
        logging.getLogger(__name__).error(f"Failed to dispatch payment receipt email: {exc}")

    return enrollment_to_out(enrollment)


@router.post("/enrollments/record-refund", response_model=PortalEnrollmentOut)
async def record_refund(
    body: PortalRefundRecord,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == body.enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enrollment.payment_status not in ("paid_online", "paid_offline", "token_paid", "partially_paid"):
        raise HTTPException(status_code=400, detail="Enrollment has no refundable payment")
    if enrollment.paid_amount <= 0:
        raise HTTPException(status_code=400, detail="Nothing to refund")
    if enrollment.status == "token_booked" and enrollment.token_expired:
        raise HTTPException(status_code=400, detail="This token booking already expired non-refundable due to non-appearance")

    refund_amount = round(float(body.amount), 2)
    if refund_amount <= 0:
        raise HTTPException(status_code=400, detail="Refund amount must be greater than zero")
    if refund_amount > enrollment.paid_amount + 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Refund cannot exceed paid amount (₹{enrollment.paid_amount})",
        )

    if (
        enrollment.payment_status in ("paid_online", "token_paid", "partially_paid")
        and body.refund_via_gateway
        and body.refund_mode == "gateway"
    ):
        order_result = await db.execute(
            select(TrainingPortalPaymentOrder)
            .where(
                TrainingPortalPaymentOrder.enrollment_id == enrollment.id,
                TrainingPortalPaymentOrder.status == "paid",
                TrainingPortalPaymentOrder.provider_payment_id.isnot(None),
            )
            .order_by(TrainingPortalPaymentOrder.paid_at.desc())
        )
        order = order_result.scalar_one_or_none()
        if order and order.provider_payment_id:
            amount_paise = int(round(refund_amount * 100))
            is_partial = refund_amount < enrollment.paid_amount - 0.01
            await create_razorpay_refund(
                order.provider_payment_id,
                amount_paise=amount_paise if is_partial else None,
            )
            if not is_partial:
                order.status = "refunded"
            else:
                order.status = "partially_refunded"
            order.updated_at = datetime.utcnow()

    new_paid = round(max(0.0, enrollment.paid_amount - refund_amount), 2)
    enrollment.paid_amount = new_paid
    enrollment.balance_due = round(max(0.0, enrollment.total_fee - new_paid), 2)

    is_fully_refunded = new_paid <= 0
    if is_fully_refunded:
        enrollment.payment_status = "refunded"
    elif enrollment.balance_due > 0:
        enrollment.payment_status = "pending"

    refund_date = body.date or datetime.utcnow().strftime("%Y-%m-%d")
    refund_note = (
        f"Refund of ₹{refund_amount:,.2f} via {body.refund_mode} on {refund_date}"
        + (f". {body.notes}" if body.notes else "")
    )
    enrollment.notes = f"{enrollment.notes}\n{refund_note}".strip() if enrollment.notes else refund_note
    enrollment.updated_at = datetime.utcnow()

    if is_fully_refunded:
        # A fully refunded enrollment is no longer a real enrollment — unlink it from
        # the course/batch entirely (releases the seat) regardless of whether it started
        # as a token booking, a paid-in-full course, or an internship application.
        enrollment.status = "dropped"
        enrollment.batch_id = None
        enrollment.preferred_batch_id = None
        enrollment.refunded_at = datetime.utcnow()
        enrollment.refund_reason = body.notes or "Refunded by SuperAdmin"
        enrollment.refunded_by_id = current_user.id
        if enrollment.enrollment_type == "internship":
            await _refresh_internship_seats(db, enrollment.item_id)
    await _record_transaction(
        db,
        enrollment=enrollment,
        transaction_type="refund",
        amount=refund_amount,
        payment_mode=body.refund_mode,
        status="completed",
        provider="razorpay" if body.refund_mode == "gateway" else "offline",
        notes=refund_note,
        created_by_id=current_user.id,
    )
    await db.commit()
    return enrollment_to_out(enrollment)


# ── Batches ───────────────────────────────────────────────────────────────────

@router.get("/batches", response_model=List[PortalBatchOut])
async def list_batches(
    course_id: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalBatch).order_by(TrainingPortalBatch.created_at.desc())
    if course_id:
        query = query.where(TrainingPortalBatch.course_id == course_id)
    result = await db.execute(query)
    rows = result.scalars().all()
    return [await batch_to_out(db, row) for row in rows]


@router.post("/batches", response_model=PortalBatchOut, status_code=status.HTTP_201_CREATED)
async def create_batch(
    body: PortalBatchCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    if len(body.enrollment_ids) > MAX_BATCH_STUDENTS:
        raise HTTPException(status_code=400, detail=f"Cannot assign more than {MAX_BATCH_STUDENTS} students at once")

    resolved_instructor_id, resolved_instructor_name = await _resolve_batch_instructor(
        db, body.instructor_id, body.instructor_name
    )

    batch = TrainingPortalBatch(
        id=str(uuid.uuid4()),
        course_id=body.course_id,
        batch_name=body.batch_name.strip(),
        instructor_id=resolved_instructor_id,
        instructor_name=resolved_instructor_name,
        start_date=body.start_date,
        end_date=body.end_date,
        days=body.days,
        time_slot=body.time,
        venue=body.venue,
        max_seats=body.max_seats or MAX_BATCH_STUDENTS,
        delivery_mode=body.delivery_mode,
        status=body.status,
        covered_topics=[],
        created_by_id=current_user.id,
    )
    db.add(batch)
    await db.commit()

    if batch.instructor_name:
        teacher_email = await _lookup_teacher_email(db, batch.instructor_name)
        if teacher_email:
            db.add(
                TrainingPortalCandidateNotification(
                    id=str(uuid.uuid4()),
                    candidate_email=teacher_email.lower(),
                    recipient_role="teacher",
                    notification_type="batch_assigned",
                    title="New Candidate Assigned",
                    description=f'You have been assigned to teach batch "{batch.batch_name}".',
                    detail=f"Start Date: {batch.start_date}. Days: {', '.join(batch.days or [])}.",
                    event_date=datetime.utcnow().strftime("%Y-%m-%d"),
                    severity="info",
                )
            )

    if body.enrollment_ids:
        await _assign_enrollments_to_batch(db, batch, body.enrollment_ids, background_tasks)

    await db.commit()
    return await batch_to_out(db, batch)


@router.post("/batches/{batch_id}/assign-students", response_model=PortalBatchOut)
async def assign_students_to_batch(
    batch_id: str,
    body: PortalBatchAssignStudents,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPortalBatch).where(TrainingPortalBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if not body.enrollment_ids:
        raise HTTPException(status_code=400, detail="No students selected")
    if len(body.enrollment_ids) > MAX_BATCH_STUDENTS:
        raise HTTPException(status_code=400, detail=f"Cannot assign more than {MAX_BATCH_STUDENTS} students at once")

    await _assign_enrollments_to_batch(db, batch, body.enrollment_ids, background_tasks)
    await db.commit()
    return await batch_to_out(db, batch)


@router.put("/batches/{batch_id}", response_model=PortalBatchOut)
async def update_batch(
    batch_id: str,
    body: PortalBatchUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPortalBatch).where(TrainingPortalBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    old_instructor_name = batch.instructor_name
    if body.batch_name is not None:
        batch.batch_name = body.batch_name.strip()
    if body.instructor_id is not None or body.instructor_name is not None:
        resolved_instructor_id, resolved_instructor_name = await _resolve_batch_instructor(
            db,
            body.instructor_id if body.instructor_id is not None else batch.instructor_id,
            body.instructor_name if body.instructor_name is not None else batch.instructor_name,
        )
        batch.instructor_id = resolved_instructor_id
        batch.instructor_name = resolved_instructor_name
    if body.start_date is not None:
        batch.start_date = body.start_date
    if body.end_date is not None:
        batch.end_date = body.end_date
    if body.days is not None:
        batch.days = body.days
    if body.time is not None:
        batch.time_slot = body.time
    if body.venue is not None:
        batch.venue = body.venue
    if body.max_seats is not None:
        current = await _batch_student_count(db, batch.id)
        if body.max_seats < current:
            raise HTTPException(status_code=400, detail="Max seats cannot be less than current enrollment count")
        batch.max_seats = body.max_seats
    if body.delivery_mode is not None:
        batch.delivery_mode = body.delivery_mode
    if body.status is not None:
        batch.status = body.status

    batch.updated_at = datetime.utcnow()

    if body.batch_name is not None:
        await db.execute(
            update(TrainingPortalEnrollment)
            .where(TrainingPortalEnrollment.batch_id == batch.id)
            .values(batch_name=batch.batch_name, updated_at=datetime.utcnow())
        )

    if body.enrollment_ids is not None:
        await _sync_batch_enrollments(db, batch, body.enrollment_ids, background_tasks)

    if body.instructor_name is not None and body.instructor_name.strip().lower() != (old_instructor_name or "").strip().lower():
        teacher_email = await _lookup_teacher_email(db, batch.instructor_name)
        if teacher_email:
            db.add(
                TrainingPortalCandidateNotification(
                    id=str(uuid.uuid4()),
                    candidate_email=teacher_email.lower(),
                    recipient_role="teacher",
                    notification_type="batch_assigned",
                    title="New Candidate Assigned",
                    description=f'You have been assigned to teach batch "{batch.batch_name}".',
                    detail=f"Start Date: {batch.start_date}. Days: {', '.join(batch.days or [])}.",
                    event_date=datetime.utcnow().strftime("%Y-%m-%d"),
                    severity="info",
                )
            )

    await db.commit()
    return await batch_to_out(db, batch)


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPortalBatch).where(TrainingPortalBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    await db.execute(
        update(TrainingPortalEnrollment)
        .where(TrainingPortalEnrollment.batch_id == batch_id)
        .values(batch_id=None, batch_name=None, updated_at=datetime.utcnow())
    )
    await db.delete(batch)
    await db.commit()


async def _lookup_teacher_email(db: AsyncSession, instructor_name: str) -> Optional[str]:
    result = await db.execute(
        select(TrainingPortalTeacher).where(
            func.lower(TrainingPortalTeacher.name) == instructor_name.strip().lower()
        )
    )
    teacher = result.scalar_one_or_none()
    return teacher.email if teacher else None


async def _resolve_batch_instructor(
    db: AsyncSession,
    instructor_id: Optional[str],
    instructor_name: Optional[str],
) -> tuple[Optional[str], str]:
    """Prefer instructor_id; always return the canonical teacher name from DB."""
    teacher_id = (instructor_id or "").strip() or None
    name = (instructor_name or "").strip()

    if teacher_id:
        result = await db.execute(
            select(TrainingPortalTeacher).where(TrainingPortalTeacher.id == teacher_id)
        )
        teacher = result.scalar_one_or_none()
        if not teacher:
            raise HTTPException(status_code=400, detail="Selected teacher not found")
        return teacher.id, teacher.name

    if name:
        result = await db.execute(
            select(TrainingPortalTeacher).where(
                func.lower(TrainingPortalTeacher.name) == name.lower()
            )
        )
        teacher = result.scalar_one_or_none()
        if teacher:
            return teacher.id, teacher.name
        return None, name

    raise HTTPException(status_code=400, detail="Please select a teacher")


async def _teacher_batch_ids_for_user(db: AsyncSession, current_user: User) -> list[str]:
    user_email = (current_user.email or "").lower()
    teacher_result = await db.execute(
        select(TrainingPortalTeacher).where(
            func.lower(TrainingPortalTeacher.email) == user_email
        )
    )
    teacher = teacher_result.scalar_one_or_none()
    teacher_name = teacher.name if teacher else _user_display_name(current_user, "Teacher")
    teacher_id = teacher.id if teacher else None
    conditions = [
        func.lower(TrainingPortalBatch.instructor_name) == teacher_name.strip().lower(),
    ]
    if teacher_id:
        conditions.append(TrainingPortalBatch.instructor_id == teacher_id)
    batch_result = await db.execute(
        select(TrainingPortalBatch.id).where(or_(*conditions))
    )
    return [row[0] for row in batch_result.all()]


# ── Class sessions ────────────────────────────────────────────────────────────

@router.get("/class-sessions", response_model=List[PortalClassSessionOut])
async def list_class_sessions(
    batch_id: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalClassSession).order_by(TrainingPortalClassSession.date.desc())
    if batch_id:
        query = query.where(TrainingPortalClassSession.batch_id == batch_id)
    result = await db.execute(query)
    return [session_to_out(row) for row in result.scalars().all()]


def _normalize_schedule_type(value: Optional[str]) -> str:
    """API uses one_time; tolerate legacy one-time."""
    normalized = (value or "one_time").strip().lower().replace("-", "_")
    return "recurring" if normalized == "recurring" else "one_time"


def _day_abbr_for_iso(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str).strftime("%a")
    except (ValueError, TypeError):
        return None


def _date_ranges_overlap(
    start_a: Optional[str],
    end_a: Optional[str],
    start_b: Optional[str],
    end_b: Optional[str],
) -> bool:
    if not start_a or not end_a or not start_b or not end_b:
        return True
    return start_a <= end_b and start_b <= end_a


async def _session_date_range(
    db: AsyncSession,
    schedule_type: str,
    date_str: Optional[str],
    batch_id: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    if schedule_type != "recurring":
        return date_str, date_str
    if batch_id:
        result = await db.execute(
            select(TrainingPortalBatch).where(TrainingPortalBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if batch:
            return batch.start_date, batch.end_date
    return date_str, date_str


def _schedules_can_share_day(
    type_a: str,
    date_a: Optional[str],
    days_a: list[str],
    range_start_a: Optional[str],
    range_end_a: Optional[str],
    type_b: str,
    date_b: Optional[str],
    days_b: list[str],
    range_start_b: Optional[str],
    range_end_b: Optional[str],
) -> bool:
    """True when the two schedules can land on the same calendar day."""
    if not _date_ranges_overlap(range_start_a, range_end_a, range_start_b, range_end_b):
        return False

    if type_a == "one_time" and type_b == "one_time":
        return bool(date_a and date_b and date_a == date_b)

    if type_a == "recurring" and type_b == "recurring":
        return bool(set(days_a) & set(days_b))

    # Mixed: one-time date weekday must be in the recurring weekdays
    if type_a == "one_time":
        day_abbr = _day_abbr_for_iso(date_a)
        return bool(day_abbr and day_abbr in days_b)
    day_abbr = _day_abbr_for_iso(date_b)
    return bool(day_abbr and day_abbr in days_a)


async def _validate_instructor_schedule(
    db: AsyncSession,
    instructor_name: Optional[str],
    start_time: str,
    end_time: str,
    schedule_type: str,
    date_str: Optional[str],
    days: Optional[List[str]],
    ignore_session_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    extra_ignore_session_ids: Optional[List[str]] = None,
    is_postponed: bool = False,
    is_admin_override: bool = False,
    note: Optional[str] = None,
):
    """Block scheduling when the same teacher already has an overlapping class."""
    if is_postponed or is_admin_override or (note and "__RECURRING_SKIP__" in note):
        return

    if not instructor_name or not instructor_name.strip():
        return

    t1_start = _parse_time_12h(start_time)
    t1_end = _parse_time_12h(end_time)
    if not t1_start or not t1_end:
        return
    if t1_start >= t1_end:
        raise HTTPException(
            status_code=400,
            detail="Class end time must be after start time.",
        )

    ignored_ids = {
        sid for sid in [ignore_session_id, *(extra_ignore_session_ids or [])] if sid
    }

    new_type = _normalize_schedule_type(schedule_type)
    new_days = list(days or [])
    new_range_start, new_range_end = await _session_date_range(
        db, new_type, date_str, batch_id
    )

    result = await db.execute(
        select(TrainingPortalClassSession).where(
            func.lower(TrainingPortalClassSession.instructor_name) == instructor_name.strip().lower()
        )
    )
    existing_sessions = result.scalars().all()

    batch_ids = {s.batch_id for s in existing_sessions if s.batch_id}
    if batch_id:
        batch_ids.add(batch_id)
    batch_ranges: dict[str, tuple[Optional[str], Optional[str]]] = {}
    if batch_ids:
        batch_result = await db.execute(
            select(TrainingPortalBatch).where(TrainingPortalBatch.id.in_(batch_ids))
        )
        for batch in batch_result.scalars().all():
            batch_ranges[batch.id] = (batch.start_date, batch.end_date)

    for existing in existing_sessions:
        if existing.id in ignored_ids:
            continue
        if existing.postponed:
            continue

        existing_type = _normalize_schedule_type(existing.schedule_type or "one_time")
        existing_days = list(existing.days or [])
        existing_batch_start, existing_batch_end = batch_ranges.get(
            existing.batch_id or "", (None, None)
        )
        if existing_type == "recurring":
            existing_range_start = existing_batch_start or existing.date
            existing_range_end = existing_batch_end or existing.date
        else:
            existing_range_start = existing.date
            existing_range_end = existing.date

        if not _schedules_can_share_day(
            new_type,
            date_str,
            new_days,
            new_range_start,
            new_range_end,
            existing_type,
            existing.date,
            existing_days,
            existing_range_start,
            existing_range_end,
        ):
            continue

        t2_start = _parse_time_12h(existing.start_time)
        t2_end = _parse_time_12h(existing.end_time)
        if not t2_start or not t2_end:
            continue

        # Overlap: Start1 < End2 and Start2 < End1
        if t1_start < t2_end and t2_start < t1_end:
            if existing_type == "one_time":
                when = f"on {existing.date}"
            else:
                days_label = ", ".join(existing_days) or "weekly"
                when = f"every {days_label}"
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Teacher {instructor_name} already has another class "
                    f"\"{existing.title}\" {when} "
                    f"({existing.start_time} – {existing.end_time}). "
                    f"Choose a different teacher, date, or time slot."
                ),
            )


@router.post("/class-sessions", response_model=PortalClassSessionOut, status_code=status.HTTP_201_CREATED)
async def create_class_session(
    body: PortalClassSessionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    if not time_within_working_hours(body.start_time) or not time_within_working_hours(body.end_time):
        raise HTTPException(
            status_code=400,
            detail="Class start and end time must be between 8:00 AM and 8:00 PM.",
        )

    await _validate_instructor_schedule(
        db=db,
        instructor_name=body.instructor_name,
        start_time=body.start_time,
        end_time=body.end_time,
        schedule_type=body.schedule_type,
        date_str=body.date,
        days=body.days,
        batch_id=body.batch_id,
        ignore_session_id=body.ignore_session_id,
        is_postponed=body.postponed,
        is_admin_override=body.admin_override,
        note=body.note,
    )

    if body.batch_id:
        student_count = await _batch_student_count(db, body.batch_id)
        if student_count < MIN_BATCH_SCHEDULE_STUDENTS and not body.admin_override:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Batch needs at least {MIN_BATCH_SCHEDULE_STUDENTS} students before scheduling. "
                    f"Currently {student_count}. Use admin override to schedule anyway."
                ),
            )

    session = TrainingPortalClassSession(
        id=str(uuid.uuid4()),
        batch_id=body.batch_id,
        item_id=body.item_id,
        title=body.title,
        instructor_name=body.instructor_name,
        date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
        days=body.days,
        venue=body.venue,
        note=body.note,
        schedule_type=body.schedule_type,
        postponed=body.postponed,
        teacher_unavailable=body.teacher_unavailable,
        created_by_id=current_user.id,
    )
    db.add(session)
    await db.commit()

    # Trigger Notifications
    if session.batch_id:
        enrollments_result = await db.execute(
            select(TrainingPortalEnrollment).where(
                TrainingPortalEnrollment.batch_id == session.batch_id,
                TrainingPortalEnrollment.status != "dropped",
            )
        )
        for enrollment in enrollments_result.scalars().all():
            db.add(
                TrainingPortalCandidateNotification(
                    id=str(uuid.uuid4()),
                    candidate_email=enrollment.candidate_email,
                    recipient_role="candidate",
                    notification_type="class_scheduled",
                    title="Class Scheduled",
                    description=f'A new class "{session.title}" has been scheduled for your batch.',
                    detail=f"Date: {session.date}. Time: {session.start_time} - {session.end_time}. Venue: {session.venue or 'TBA'}.",
                    event_date=session.date,
                    severity="info",
                )
            )

    teacher_email = await _lookup_teacher_email(db, session.instructor_name)
    if teacher_email:
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=teacher_email.lower(),
                recipient_role="teacher",
                notification_type="class_scheduled",
                title="Class Scheduled",
                description=f'You have been scheduled to teach class "{session.title}".',
                detail=f"Date: {session.date}. Time: {session.start_time} - {session.end_time}. Venue: {session.venue or 'TBA'}.",
                event_date=session.date,
                severity="info",
            )
        )

    background_tasks.add_task(run_class_sync, session.id)
    return session_to_out(session)


@router.put("/class-sessions/{session_id}", response_model=PortalClassSessionOut)
async def update_class_session(
    session_id: str,
    body: PortalClassSessionUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")

    effective_start_time = body.start_time if body.start_time is not None else session.start_time
    effective_end_time = body.end_time if body.end_time is not None else session.end_time
    if not time_within_working_hours(effective_start_time) or not time_within_working_hours(effective_end_time):
        raise HTTPException(
            status_code=400,
            detail="Class start and end time must be between 8:00 AM and 8:00 PM.",
        )

    effective_instructor = body.instructor_name if body.instructor_name is not None else session.instructor_name
    effective_schedule_type = body.schedule_type if body.schedule_type is not None else session.schedule_type
    effective_date = body.date if body.date is not None else session.date
    effective_days = body.days if body.days is not None else session.days

    await _validate_instructor_schedule(
        db=db,
        instructor_name=effective_instructor,
        start_time=effective_start_time,
        end_time=effective_end_time,
        schedule_type=effective_schedule_type,
        date_str=effective_date,
        days=effective_days,
        ignore_session_id=session_id,
        batch_id=body.batch_id if body.batch_id is not None else session.batch_id,
        extra_ignore_session_ids=[body.ignore_session_id] if body.ignore_session_id else None,
        is_postponed=body.postponed if body.postponed is not None else session.postponed,
        is_admin_override=body.admin_override if body.admin_override is not None else False,
        note=body.note if body.note is not None else session.note,
    )

    batch_id = body.batch_id if body.batch_id is not None else session.batch_id
    if batch_id:
        student_count = await _batch_student_count(db, batch_id)
        if student_count < MIN_BATCH_SCHEDULE_STUDENTS and not body.admin_override:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Batch needs at least {MIN_BATCH_SCHEDULE_STUDENTS} students before scheduling. "
                    f"Currently {student_count}. Use admin override to schedule anyway."
                ),
            )

    updates = body.model_dump(exclude_unset=True, exclude={"admin_override", "ignore_session_id"})
    for field, value in updates.items():
        setattr(session, field, value)
    session.updated_at = datetime.utcnow()
    await db.commit()
    background_tasks.add_task(run_class_sync, session.id)
    return session_to_out(session)


CLASS_SESSION_ATTACHMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".png", ".jpg", ".jpeg",
}


@router.post("/class-sessions/{session_id}/attachment", response_model=PortalClassSessionOut)
async def upload_class_session_attachment(
    session_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_teacher_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")

    ext = Path(file.filename or "attachment").suffix.lower()
    if ext not in CLASS_SESSION_ATTACHMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, Word, PowerPoint, Excel, text, or image files are allowed.",
        )

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.MAX_UPLOAD_MB}MB allowed.")

    base_dir = get_upload_dir()
    if not base_dir.is_absolute():
        base_dir = get_upload_dir()
    attachment_dir = base_dir / "training_portal_class_session_attachments"
    attachment_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = attachment_dir / safe_name
    with open(file_path, "wb") as output_file:
        output_file.write(content)

    session.attachment_url = f"/uploads/training_portal_class_session_attachments/{safe_name}"
    session.attachment_filename = file.filename or safe_name
    session.updated_at = datetime.utcnow()
    await db.commit()
    return session_to_out(session)


@router.delete("/class-sessions/{session_id}/attachment", response_model=PortalClassSessionOut)
async def delete_class_session_attachment(
    session_id: str,
    current_user: User = Depends(require_teacher_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")

    session.attachment_url = None
    session.attachment_filename = None
    session.updated_at = datetime.utcnow()
    await db.commit()
    return session_to_out(session)


@router.delete("/class-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class_session(
    session_id: str,
    scope: Optional[str] = Query("single"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")

    sessions_to_delete = [session]
    if scope in ("series", "recurring", "all"):
        if session.batch_id:
            batch_result = await db.execute(
                select(TrainingPortalClassSession).where(
                    TrainingPortalClassSession.batch_id == session.batch_id
                )
            )
            sessions_to_delete = batch_result.scalars().all()
        elif session.instructor_name and session.title:
            matching_result = await db.execute(
                select(TrainingPortalClassSession).where(
                    func.lower(TrainingPortalClassSession.instructor_name) == session.instructor_name.strip().lower(),
                    func.lower(TrainingPortalClassSession.title) == session.title.strip().lower(),
                )
            )
            sessions_to_delete = matching_result.scalars().all()

    for target in sessions_to_delete:
        cancel_snapshot = await build_cancel_snapshot(db, target.id)
        await db.delete(target)
        if cancel_snapshot:
            background_tasks.add_task(run_class_cancel, cancel_snapshot)

    await db.commit()
    return None


@router.get("/class-sessions/today", response_model=List[PortalClassSessionOut])
async def list_todays_class_sessions(
    instructor_name: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    today = today_ist()
    now = now_ist()
    filter_name = (instructor_name or "").strip()

    result = await db.execute(
        select(TrainingPortalClassSession).order_by(TrainingPortalClassSession.start_time.asc())
    )
    all_sessions = list(result.scalars().all())
    todays: list[TrainingPortalClassSession] = []

    for session in all_sessions:
        if filter_name and session.instructor_name.strip().lower() != filter_name.lower():
            continue
        if not session_occurs_on_date(session, today):
            continue
        todays.append(session)
        # Start reminders, 15-min end reminder, and auto-end at scheduled end_time.
        await process_todays_session_lifecycle(db, session, today, now)

    await db.commit()
    return [session_to_out_for_date(row, today, now) for row in todays]


@router.post("/class-sessions/{session_id}/start", response_model=PortalClassSessionOut)
async def start_class_session(
    session_id: str,
    body: PortalClassSessionStart = PortalClassSessionStart(),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")

    if session.batch_id:
        enrollments_count_result = await db.execute(
            select(func.count()).select_from(TrainingPortalEnrollment).where(
                TrainingPortalEnrollment.batch_id == session.batch_id,
                TrainingPortalEnrollment.status != "dropped"
            )
        )
        count = int(enrollments_count_result.scalar() or 0)
        if count == 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot start class session because there are no students enrolled in this batch"
            )

    today = today_ist()
    now = now_ist()
    if not session_occurs_on_date(session, today):
        raise HTTPException(status_code=400, detail="This session is not scheduled for today")

    effective = effective_live_status(session, now, today)
    if effective == "live":
        return session_to_out_for_date(session, today, now)
    if effective in {"completed", "missed"}:
        raise HTTPException(status_code=400, detail="Class session cannot be started")

    if not should_show_start_button(session, now, today):
        raise HTTPException(status_code=400, detail="Class can only be started between scheduled start and end time")

    if is_late_start(session, now, today):
        reason = (body.late_start_reason or "").strip()
        if len(reason) < 10:
            raise HTTPException(
                status_code=400,
                detail="Late start reason is required when starting after scheduled time (min 10 characters)",
            )
        session.late_start_reason = reason
    else:
        session.late_start_reason = None

    if not session_live_applies_to_date(session, today):
        session.early_end_reason = None
        session.session_report = None
        session.covered_topic_ids = []
        session.attachment_url = None
        session.attachment_filename = None
        session.attendance_marked = False
        session.end_reminder_sent = False

    session.live_status = "live"
    session.live_occurrence_date = today.isoformat()
    session.started_at = now
    session.ended_at = None
    session.updated_at = now
    await db.commit()
    return session_to_out_for_date(session, today, now)


@router.get("/class-sessions/{session_id}/roster", response_model=List[PortalSessionStudentOut])
async def get_class_session_roster(
    session_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")
    if not session.batch_id:
        return []

    enrollments_result = await db.execute(
        select(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.batch_id == session.batch_id,
            TrainingPortalEnrollment.status != "dropped",
        ).order_by(TrainingPortalEnrollment.candidate_name.asc())
    )
    enrollments = list(enrollments_result.scalars().all())
    today_str = today_ist().isoformat()
    approved_leaves_result = await db.execute(
        select(TrainingPortalLeaveRequest).where(
            TrainingPortalLeaveRequest.requester_type == "student",
            TrainingPortalLeaveRequest.batch_id == session.batch_id,
            TrainingPortalLeaveRequest.date == today_str,
            TrainingPortalLeaveRequest.status == "approved",
        )
    )
    approved_emails = {
        (row.candidate_email or "").lower()
        for row in approved_leaves_result.scalars().all()
    }
    return [
        PortalSessionStudentOut(
            enrollment_id=e.id,
            candidate_name=e.candidate_name,
            candidate_email=e.candidate_email,
            approved_leave=e.candidate_email.lower() in approved_emails,
        )
        for e in enrollments
    ]


@router.post("/class-sessions/{session_id}/complete", response_model=PortalClassSessionOut)
async def complete_class_session(
    session_id: str,
    body: PortalClassSessionComplete,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")

    today = today_ist()
    now = now_ist()
    if not session_occurs_on_date(session, today):
        raise HTTPException(status_code=400, detail="This session is not scheduled for today")
    if effective_live_status(session, now, today) != "live":
        raise HTTPException(status_code=400, detail="Class must be started before completing")
    if not body.attendance:
        raise HTTPException(status_code=400, detail="Attendance records are required")

    occurrence_date = today.isoformat()

    if is_early_end(session, now, today):
        reason = (body.early_end_reason or "").strip()
        if len(reason) < 10:
            raise HTTPException(
                status_code=400,
                detail="Early end reason is required when ending before scheduled time (min 10 characters)",
            )
        session.early_end_reason = reason

    batch = None
    if session.batch_id:
        batch_result = await db.execute(
            select(TrainingPortalBatch).where(TrainingPortalBatch.id == session.batch_id)
        )
        batch = batch_result.scalar_one_or_none()

    enrollment_ids = [entry.enrollment_id for entry in body.attendance]
    enrollments_map = {}
    approved_leave_emails = set()
    existing_records_map = {}

    if enrollment_ids:
        e_res = await db.execute(
            select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id.in_(enrollment_ids))
        )
        enrollments_map = {e.id: e for e in e_res.scalars().all()}

        candidate_emails = [e.candidate_email.lower() for e in enrollments_map.values() if e.candidate_email]
        if candidate_emails and session.batch_id:
            l_res = await db.execute(
                select(func.lower(TrainingPortalLeaveRequest.candidate_email)).where(
                    TrainingPortalLeaveRequest.requester_type == "student",
                    func.lower(TrainingPortalLeaveRequest.candidate_email).in_(candidate_emails),
                    TrainingPortalLeaveRequest.batch_id == session.batch_id,
                    TrainingPortalLeaveRequest.date == occurrence_date,
                    TrainingPortalLeaveRequest.status == "approved",
                )
            )
            approved_leave_emails = set(l_res.scalars().all())

        att_res = await db.execute(
            select(TrainingPortalAttendanceRecord).where(
                TrainingPortalAttendanceRecord.class_session_id == session.id,
                TrainingPortalAttendanceRecord.enrollment_id.in_(enrollment_ids),
                TrainingPortalAttendanceRecord.occurrence_date == occurrence_date,
            )
        )
        existing_records_map = {att.enrollment_id: att for att in att_res.scalars().all()}

    for entry in body.attendance:
        enrollment = enrollments_map.get(entry.enrollment_id)
        if not enrollment:
            raise HTTPException(status_code=400, detail=f"Enrollment {entry.enrollment_id} not found")
        if session.batch_id and enrollment.batch_id != session.batch_id:
            raise HTTPException(status_code=400, detail="Student not in this batch")

        email_clean = (enrollment.candidate_email or "").lower()
        is_on_leave = email_clean in approved_leave_emails
        status_to_mark = "on_leave" if is_on_leave else entry.status

        record = existing_records_map.get(entry.enrollment_id)
        if record:
            record.status = status_to_mark
            record.marked_at = now
            record.marked_by_id = current_user.id
        else:
            db.add(
                TrainingPortalAttendanceRecord(
                    id=str(uuid.uuid4()),
                    class_session_id=session.id,
                    enrollment_id=entry.enrollment_id,
                    occurrence_date=occurrence_date,
                    batch_id=session.batch_id,
                    candidate_email=enrollment.candidate_email,
                    candidate_name=enrollment.candidate_name,
                    status=status_to_mark,
                    marked_by_id=current_user.id,
                    marked_at=now,
                )
            )

        if enrollment.candidate_email:
            sev = "success" if status_to_mark == "present" else ("warning" if status_to_mark == "late" else ("danger" if status_to_mark == "absent" else "info"))
            status_label = status_to_mark.replace("_", " ").title()
            db.add(
                TrainingPortalCandidateNotification(
                    id=str(uuid.uuid4()),
                    candidate_email=enrollment.candidate_email.lower(),
                    recipient_role="candidate",
                    notification_type="attendance_marked",
                    title=f"Attendance Marked: {status_label}",
                    description=f'Your attendance for "{session.title}" on {occurrence_date} has been marked as {status_label}.',
                    detail=f"Class: {session.title}. Time: {session.start_time} - {session.end_time}. Status: {status_label}.",
                    event_date=occurrence_date,
                    severity=sev,
                )
            )

    session.live_status = "completed"
    session.live_occurrence_date = occurrence_date
    session.ended_at = now
    session.attendance_marked = True
    session.session_report = (body.session_report or "").strip() or None
    session.covered_topic_ids = list(body.covered_topic_ids or [])
    session.updated_at = now

    if batch and body.covered_topic_ids:
        merged = list(dict.fromkeys([*(batch.covered_topics or []), *body.covered_topic_ids]))
        batch.covered_topics = merged
        batch.updated_at = datetime.utcnow()
        await _recalculate_batch_progress(db, batch)
    elif batch:
        await _recalculate_batch_progress(db, batch)

    await db.commit()
    return session_to_out_for_date(session, today, now)


# ── Attendance records ────────────────────────────────────────────────────────

@router.get("/attendance-records", response_model=List[PortalAttendanceRecordOut])
async def list_attendance_records(
    batch_id: Optional[str] = Query(None),
    candidate_email: Optional[str] = Query(None),
    class_session_id: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(TrainingPortalAttendanceRecord, TrainingPortalClassSession)
        .join(
            TrainingPortalClassSession,
            TrainingPortalAttendanceRecord.class_session_id == TrainingPortalClassSession.id,
        )
        .order_by(TrainingPortalAttendanceRecord.marked_at.desc())
    )
    if class_session_id:
        query = query.where(TrainingPortalAttendanceRecord.class_session_id == class_session_id)

    is_admin = getattr(current_user, "is_super_admin", False)
    user_email = (current_user.email or "").lower()
    user_role = getattr(current_user, "role", None)

    teacher_batch_ids: Optional[list[str]] = None
    if user_role == "teacher" and not is_admin:
        teacher_batch_ids = await _teacher_batch_ids_for_user(db, current_user)
        if not teacher_batch_ids:
            return []

    if batch_id:
        if teacher_batch_ids is not None and batch_id not in teacher_batch_ids:
            raise HTTPException(status_code=403, detail="Not authorized for this batch")
        query = query.where(TrainingPortalAttendanceRecord.batch_id == batch_id)
    elif teacher_batch_ids is not None:
        query = query.where(TrainingPortalAttendanceRecord.batch_id.in_(teacher_batch_ids))

    is_student = not is_admin and teacher_batch_ids is None
    if candidate_email:
        normalized_candidate_email = candidate_email.strip().lower()
        if is_student and normalized_candidate_email != user_email:
            raise HTTPException(status_code=403, detail="Not authorized to view another candidate's records")
        query = query.where(
            TrainingPortalAttendanceRecord.candidate_email == normalized_candidate_email
        )
    elif is_student:
        query = query.where(TrainingPortalAttendanceRecord.candidate_email == user_email)

    result = await db.execute(query)
    rows = result.all()
    return [
        PortalAttendanceRecordOut(
            id=record.id,
            class_session_id=record.class_session_id,
            enrollment_id=record.enrollment_id,
            batch_id=record.batch_id,
            candidate_email=record.candidate_email,
            candidate_name=record.candidate_name,
            status=record.status,
            marked_at=record.marked_at,
            session_title=session.title,
            session_date=(record.occurrence_date or None) or session.date,
            session_start_time=session.start_time,
            session_end_time=session.end_time,
            session_report=session.session_report,
            covered_topic_ids=session.covered_topic_ids or [],
            attachment_url=session.attachment_url,
            attachment_filename=session.attachment_filename,
            late_start_reason=session.late_start_reason,
            early_end_reason=session.early_end_reason,
            instructor_name=session.instructor_name,
            occurrence_date=record.occurrence_date or None,
        )
        for record, session in rows
    ]


# ── Leave requests ────────────────────────────────────────────────────────────

def _leave_status_label(status: str) -> str:
    return status.strip().lower()


async def _notify_leave_status(
    db: AsyncSession,
    leave: TrainingPortalLeaveRequest,
    status: str,
):
    email = (leave.candidate_email or leave.teacher_email or "").lower()
    if not email:
        return
    label = "approved" if status == "approved" else "rejected"
    role = "teacher" if leave.teacher_email else "candidate"
    db.add(
        TrainingPortalCandidateNotification(
            id=str(uuid.uuid4()),
            candidate_email=email,
            recipient_role=role,
            notification_type="leave_status",
            title=f"Leave request {label}",
            description=f"Your leave for {leave.date} has been {label}.",
            detail=leave.review_note or leave.reason,
            event_date=leave.date,
            severity="success" if status == "approved" else "danger",
        )
    )


@router.get("/leave-requests", response_model=List[PortalLeaveRequestOut])
async def list_leave_requests(
    batch_id: Optional[str] = Query(None),
    requester_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    candidate_email: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalLeaveRequest).order_by(TrainingPortalLeaveRequest.created_at.desc())
    is_admin = getattr(current_user, "is_super_admin", False)
    user_email = (current_user.email or "").lower()
    user_role = getattr(current_user, "role", None)

    if batch_id:
        query = query.where(TrainingPortalLeaveRequest.batch_id == batch_id)
    if requester_type:
        query = query.where(TrainingPortalLeaveRequest.requester_type == requester_type.strip().lower())
    if status:
        query = query.where(TrainingPortalLeaveRequest.status == _leave_status_label(status))

    if is_admin:
        if candidate_email:
            query = query.where(
                TrainingPortalLeaveRequest.candidate_email == candidate_email.strip().lower()
            )
    elif user_role == "teacher":
        teacher_result = await db.execute(
            select(TrainingPortalTeacher).where(
                func.lower(TrainingPortalTeacher.email) == user_email
            )
        )
        teacher = teacher_result.scalar_one_or_none()
        teacher_name = teacher.name if teacher else _user_display_name(current_user, "Teacher")
        batch_result = await db.execute(
            select(TrainingPortalBatch.id).where(
                func.lower(TrainingPortalBatch.instructor_name) == teacher_name.strip().lower()
            )
        )
        teacher_batch_ids = [row[0] for row in batch_result.all()]
        query = query.where(
            (TrainingPortalLeaveRequest.batch_id.in_(teacher_batch_ids))
            | (TrainingPortalLeaveRequest.teacher_email == user_email)
        )
    else:
        enrollments_result = await db.execute(
            select(TrainingPortalEnrollment.batch_id).where(
                func.lower(TrainingPortalEnrollment.candidate_email) == user_email,
                TrainingPortalEnrollment.status != "dropped",
                TrainingPortalEnrollment.batch_id.isnot(None),
            )
        )
        enrolled_batch_ids = [row[0] for row in enrollments_result.all() if row[0]]
        instructor_names: set[str] = set()
        if enrolled_batch_ids:
            batch_rows = await db.execute(
                select(TrainingPortalBatch.instructor_name).where(
                    TrainingPortalBatch.id.in_(enrolled_batch_ids)
                )
            )
            instructor_names = {
                (row[0] or "").strip().lower()
                for row in batch_rows.all()
                if row[0]
            }

        student_own = TrainingPortalLeaveRequest.candidate_email == user_email
        if instructor_names:
            teacher_approved = and_(
                TrainingPortalLeaveRequest.requester_type == "teacher",
                TrainingPortalLeaveRequest.status == "approved",
                func.lower(TrainingPortalLeaveRequest.teacher_name).in_(instructor_names),
            )
            query = query.where(or_(student_own, teacher_approved))
        else:
            query = query.where(student_own)

    result = await db.execute(query)
    return [leave_to_out(row) for row in result.scalars().all()]


@router.post("/leave-requests", response_model=PortalLeaveRequestOut, status_code=status.HTTP_201_CREATED)
async def create_student_leave_request(
    body: PortalLeaveRequestCreate,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    reason = body.reason.strip()
    if len(reason) < 10:
        raise HTTPException(status_code=400, detail="Leave reason must be at least 10 characters")

    # Check if student already has a pending or approved leave request for the same date
    existing_result = await db.execute(
        select(TrainingPortalLeaveRequest).where(
            TrainingPortalLeaveRequest.requester_type == "student",
            func.lower(TrainingPortalLeaveRequest.candidate_email) == (current_user.email or "").lower(),
            TrainingPortalLeaveRequest.date == body.date,
            TrainingPortalLeaveRequest.status.in_(["pending", "approved"]),
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied for leave on this date",
        )

    leave = TrainingPortalLeaveRequest(
        id=str(uuid.uuid4()),
        requester_type="student",
        candidate_email=(current_user.email or "").lower(),
        candidate_name=_user_display_name(current_user, "Student"),
        session_id=body.session_id,
        date=body.date,
        batch_id=body.batch_id,
        batch_name=body.batch_name,
        reason=reason,
        status="pending",
    )
    db.add(leave)
    await db.commit()

    # Notify batch teacher
    if body.batch_id:
        batch_res = await db.execute(select(TrainingPortalBatch).where(TrainingPortalBatch.id == body.batch_id))
        batch = batch_res.scalar_one_or_none()
        if batch and batch.instructor_name:
            t_email = await _lookup_teacher_email(db, batch.instructor_name)
            if t_email:
                db.add(
                    TrainingPortalCandidateNotification(
                        id=str(uuid.uuid4()),
                        candidate_email=t_email.lower(),
                        recipient_role="teacher",
                        notification_type="student_leave_submitted",
                        title="Student Leave Request",
                        description=f"{leave.candidate_name} has requested leave for {leave.date}.",
                        detail=reason,
                        event_date=leave.date,
                        severity="info",
                    )
                )
                await db.commit()

    return leave_to_out(leave)


@router.post("/leave-requests/teacher", response_model=PortalLeaveRequestOut, status_code=status.HTTP_201_CREATED)
async def create_teacher_leave_request(
    body: PortalTeacherLeaveRequestCreate,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    if getattr(current_user, "role", None) != "teacher" and not getattr(current_user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Only teachers can submit teacher leave requests")

    reason = body.reason.strip()
    if len(reason) < 10:
        raise HTTPException(status_code=400, detail="Leave reason must be at least 10 characters")

    # Check if teacher already has a pending or approved leave request for the same date
    existing_result = await db.execute(
        select(TrainingPortalLeaveRequest).where(
            TrainingPortalLeaveRequest.requester_type == "teacher",
            func.lower(TrainingPortalLeaveRequest.teacher_email) == (current_user.email or "").lower(),
            TrainingPortalLeaveRequest.date == body.date,
            TrainingPortalLeaveRequest.status.in_(["pending", "approved"]),
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied for leave on this date",
        )

    teacher_result = await db.execute(
        select(TrainingPortalTeacher).where(
            func.lower(TrainingPortalTeacher.email) == (current_user.email or "").lower()
        )
    )
    teacher = teacher_result.scalar_one_or_none()
    teacher_name = teacher.name if teacher else _user_display_name(current_user, "Teacher")

    leave = TrainingPortalLeaveRequest(
        id=str(uuid.uuid4()),
        requester_type="teacher",
        teacher_email=(current_user.email or "").lower(),
        teacher_name=teacher_name,
        date=body.date,
        batch_id=body.batch_id,
        batch_name=body.batch_name,
        reason=reason,
        status="pending",
    )
    db.add(leave)
    await db.commit()

    # Notify admins
    admin_res = await db.execute(select(User.email).where(User.is_super_admin == True))
    admin_emails = [row[0] for row in admin_res.all()]
    for admin_email in admin_emails:
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=admin_email,
                recipient_role="admin",
                notification_type="teacher_leave_submitted",
                title="Teacher Leave Request",
                description=f"Teacher {teacher_name} has requested leave for {body.date}.",
                detail=reason,
                event_date=body.date,
                severity="info",
            )
        )
    await db.commit()

    return leave_to_out(leave)


@router.patch("/leave-requests/{leave_id}/review", response_model=PortalLeaveRequestOut)
async def review_leave_request(
    leave_id: str,
    body: PortalLeaveRequestReview,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalLeaveRequest).where(TrainingPortalLeaveRequest.id == leave_id)
    )
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if leave.status != "pending":
        raise HTTPException(status_code=400, detail="Leave request already reviewed")

    is_admin = getattr(current_user, "is_super_admin", False)
    user_role = getattr(current_user, "role", None)
    new_status = _leave_status_label(body.status)

    if leave.requester_type == "teacher":
        if not is_admin:
            raise HTTPException(status_code=403, detail="Only admin can review teacher leave requests")
        reviewer_role = "admin"
    else:
        if is_admin:
            reviewer_role = "admin"
        elif user_role == "teacher":
            if leave.batch_id:
                batch_result = await db.execute(
                    select(TrainingPortalBatch).where(TrainingPortalBatch.id == leave.batch_id)
                )
                batch = batch_result.scalar_one_or_none()
                teacher_result = await db.execute(
                    select(TrainingPortalTeacher).where(
                        func.lower(TrainingPortalTeacher.email) == (current_user.email or "").lower()
                    )
                )
                teacher = teacher_result.scalar_one_or_none()
                teacher_name = teacher.name if teacher else _user_display_name(current_user, "Teacher")
                if not batch or batch.instructor_name.strip().lower() != teacher_name.strip().lower():
                    raise HTTPException(status_code=403, detail="Not authorized to review this leave")
            reviewer_role = "teacher"
        else:
            raise HTTPException(status_code=403, detail="Not authorized to review leave requests")

    leave.status = new_status
    leave.reviewed_by_id = current_user.id
    leave.reviewed_by_role = reviewer_role
    leave.review_note = (body.review_note or "").strip() or None
    leave.updated_at = datetime.utcnow()
    await _notify_leave_status(db, leave, new_status)
    await db.commit()
    return leave_to_out(leave)


# ── Behavior reports ──────────────────────────────────────────────────────────

def _validate_behavior_rating(value: int, field: str) -> int:
    if value < 1 or value > 5:
        raise HTTPException(status_code=400, detail=f"{field} must be between 1 and 5")
    return value


@router.get("/behavior-reports", response_model=List[PortalBehaviorReportOut])
async def list_behavior_reports(
    candidate_email: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalBehaviorReport).order_by(
        TrainingPortalBehaviorReport.report_date.desc(),
        TrainingPortalBehaviorReport.created_at.desc(),
    )
    is_admin = getattr(current_user, "is_super_admin", False)
    user_role = getattr(current_user, "role", None)
    user_email = (current_user.email or "").strip().lower()

    if is_admin:
        if candidate_email:
            query = query.where(
                func.lower(TrainingPortalBehaviorReport.candidate_email) == candidate_email.strip().lower()
            )
    elif user_role == "teacher":
        teacher_batch_ids = await _teacher_batch_ids_for_user(db, current_user)
        teacher_result = await db.execute(
            select(TrainingPortalTeacher).where(func.lower(TrainingPortalTeacher.email) == user_email)
        )
        teacher = teacher_result.scalar_one_or_none()
        teacher_name = teacher.name if teacher else _user_display_name(current_user, "Teacher")
        teacher_filters = [
            func.lower(TrainingPortalBehaviorReport.teacher_email) == user_email,
            func.lower(TrainingPortalBehaviorReport.instructor_name) == teacher_name.strip().lower(),
        ]
        if teacher_batch_ids:
            teacher_filters.append(TrainingPortalBehaviorReport.batch_id.in_(teacher_batch_ids))
        query = query.where(or_(*teacher_filters))
    else:
        query = query.where(
            func.lower(TrainingPortalBehaviorReport.candidate_email) == user_email
        )

    if batch_id:
        query = query.where(TrainingPortalBehaviorReport.batch_id == batch_id)

    result = await db.execute(query)
    return [behavior_report_to_out(row) for row in result.scalars().all()]


@router.post("/behavior-reports", response_model=PortalBehaviorReportOut, status_code=status.HTTP_201_CREATED)
async def create_behavior_report(
    body: PortalBehaviorReportCreate,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    user_role = getattr(current_user, "role", None)
    is_admin = getattr(current_user, "is_super_admin", False)
    if user_role != "teacher" and not is_admin:
        raise HTTPException(status_code=403, detail="Only teachers can submit behavior reports")

    enrollment_result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == body.enrollment_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if not enrollment.batch_id:
        raise HTTPException(status_code=400, detail="Enrollment is not assigned to a batch")

    teacher_batch_ids = await _teacher_batch_ids_for_user(db, current_user)
    if not is_admin and enrollment.batch_id not in teacher_batch_ids:
        raise HTTPException(status_code=403, detail="Not authorized to submit feedback for this trainee")

    user_email = (current_user.email or "").strip().lower()
    teacher_result = await db.execute(
        select(TrainingPortalTeacher).where(func.lower(TrainingPortalTeacher.email) == user_email)
    )
    teacher = teacher_result.scalar_one_or_none()
    instructor_name = teacher.name if teacher else _user_display_name(current_user, "Teacher")
    instructor_id = teacher.id if teacher else None

    discipline = _validate_behavior_rating(body.discipline_rating, "discipline_rating")
    participation = _validate_behavior_rating(body.participation_rating, "participation_rating")
    performance = _validate_behavior_rating(body.performance_rating, "performance_rating")
    comments = (body.comments or "").strip()
    if not comments:
        raise HTTPException(status_code=400, detail="Comments are required")

    report_date = (body.report_date or date.today().isoformat()).strip()
    flagged = discipline <= 2 or performance <= 2

    report = TrainingPortalBehaviorReport(
        id=str(uuid.uuid4()),
        enrollment_id=enrollment.id,
        candidate_name=enrollment.candidate_name,
        candidate_email=enrollment.candidate_email.lower(),
        batch_id=enrollment.batch_id,
        batch_name=enrollment.batch_name,
        instructor_id=instructor_id,
        instructor_name=instructor_name,
        teacher_email=user_email,
        report_date=report_date,
        discipline_rating=discipline,
        participation_rating=participation,
        performance_rating=performance,
        comments=comments,
        flagged_for_review=flagged,
    )
    db.add(report)
    await db.commit()

    # Notify candidate
    db.add(
        TrainingPortalCandidateNotification(
            id=str(uuid.uuid4()),
            candidate_email=enrollment.candidate_email.lower(),
            recipient_role="candidate",
            notification_type="behavior_report",
            title="Behavior Feedback Report",
            description=f"Your instructor {instructor_name} has submitted a new behavior feedback report.",
            detail=f"Discipline: {discipline}/5, Participation: {participation}/5, Performance: {performance}/5. Comments: {comments}",
            event_date=report_date,
            severity="warning" if flagged else "info",
        )
    )
    await db.commit()

    return behavior_report_to_out(report)


@router.patch("/behavior-reports/{report_id}/resolve", response_model=PortalBehaviorReportOut)
async def resolve_behavior_report(
    report_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalBehaviorReport).where(TrainingPortalBehaviorReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Behavior report not found")

    report.flagged_for_review = False
    report.updated_at = datetime.utcnow()
    await db.commit()
    return behavior_report_to_out(report)


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_model=List[PortalNotificationOut])
async def list_notifications(
    candidate_email: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    role_str = "admin"
    if not getattr(current_user, "is_super_admin", False):
        role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role or "")
        role_str = "candidate" if role_val == "seeker" else role_val

    query = select(TrainingPortalCandidateNotification).order_by(
        TrainingPortalCandidateNotification.created_at.desc()
    )
    if getattr(current_user, "is_super_admin", False) and candidate_email:
        query = query.where(
            and_(
                TrainingPortalCandidateNotification.candidate_email == candidate_email,
                TrainingPortalCandidateNotification.recipient_role == "candidate"
            )
        )
    else:
        query = query.where(
            and_(
                TrainingPortalCandidateNotification.candidate_email == (current_user.email or ""),
                TrainingPortalCandidateNotification.recipient_role == role_str
            )
        )
    result = await db.execute(query)
    return [notification_to_out(row) for row in result.scalars().all()]


@router.post("/notifications/mark-read")
async def mark_notifications_read(
    body: PortalNotificationMarkRead,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    role_str = "admin"
    if not getattr(current_user, "is_super_admin", False):
        role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role or "")
        role_str = "candidate" if role_val == "seeker" else role_val

    query = select(TrainingPortalCandidateNotification).where(
        and_(
            TrainingPortalCandidateNotification.candidate_email == (current_user.email or ""),
            TrainingPortalCandidateNotification.recipient_role == role_str,
            TrainingPortalCandidateNotification.is_read == False
        )
    )
    if body.notification_ids is not None and len(body.notification_ids) > 0:
        query = query.where(TrainingPortalCandidateNotification.id.in_(body.notification_ids))

    res = await db.execute(query)
    rows = res.scalars().all()
    for row in rows:
        row.is_read = True

    await db.commit()
    return {"status": "ok", "message": f"Marked {len(rows)} notification(s) as read."}


@router.post("/notifications/clear-all")
async def clear_all_notifications(
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    role_str = "admin"
    if not getattr(current_user, "is_super_admin", False):
        role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role or "")
        role_str = "candidate" if role_val == "seeker" else role_val

    await db.execute(
        delete(TrainingPortalCandidateNotification).where(
            and_(
                TrainingPortalCandidateNotification.candidate_email == (current_user.email or ""),
                TrainingPortalCandidateNotification.recipient_role == role_str
            )
        )
    )
    await db.commit()
    return {"status": "ok", "message": "All notifications cleared."}


@router.delete("/notifications/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    role_str = "admin"
    if not getattr(current_user, "is_super_admin", False):
        role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role or "")
        role_str = "candidate" if role_val == "seeker" else role_val

    result = await db.execute(
        select(TrainingPortalCandidateNotification).where(
            and_(
                TrainingPortalCandidateNotification.id == id,
                TrainingPortalCandidateNotification.candidate_email == (current_user.email or ""),
                TrainingPortalCandidateNotification.recipient_role == role_str
            )
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(row)
    await db.commit()


# ── Transactions ──────────────────────────────────────────────────────────────

@router.get("/transactions", response_model=List[PortalTransactionOut])
async def list_transactions(
    candidate_email: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalTransaction).order_by(TrainingPortalTransaction.created_at.desc())
    is_admin = getattr(current_user, "is_super_admin", False)
    if not is_admin:
        query = query.where(TrainingPortalTransaction.candidate_email == (current_user.email or ""))
    elif candidate_email:
        query = query.where(TrainingPortalTransaction.candidate_email == candidate_email.strip().lower())
    if transaction_type:
        query = query.where(TrainingPortalTransaction.transaction_type == transaction_type.strip())
    result = await db.execute(query)
    return [transaction_to_out(row) for row in result.scalars().all()]


@router.get("/transactions/{transaction_id}/invoice", response_model=PortalPaymentInvoiceOut)
async def get_transaction_invoice(
    transaction_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalTransaction).where(TrainingPortalTransaction.transaction_id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if transaction.transaction_type != "payment":
        raise HTTPException(status_code=400, detail="Invoice is available only for payment transactions")
    if transaction.candidate_email != (current_user.email or "") and not getattr(current_user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized to view this invoice")
    if not transaction.enrollment_id:
        raise HTTPException(status_code=404, detail="Linked enrollment not found for this transaction")

    enrollment_result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == transaction.enrollment_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return await _build_invoice(db, transaction, enrollment)


@router.get("/enrollments/{enrollment_id}/invoice/latest", response_model=PortalPaymentInvoiceOut)
async def get_latest_enrollment_invoice(
    enrollment_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    enrollment_result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == enrollment_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enrollment.candidate_email != (current_user.email or "") and not getattr(current_user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized to view this invoice")

    transaction_result = await db.execute(
        select(TrainingPortalTransaction)
        .where(
            TrainingPortalTransaction.enrollment_id == enrollment_id,
            TrainingPortalTransaction.transaction_type == "payment",
        )
        .order_by(TrainingPortalTransaction.created_at.desc())
    )
    transaction = transaction_result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="No payment invoice found for this enrollment")
    return await _build_invoice(db, transaction, enrollment)


# ── Refund requests ───────────────────────────────────────────────────────────

@router.get("/refund-requests/eligibility/{enrollment_id}")
async def refund_request_eligibility(
    enrollment_id: str,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enrollment.candidate_email != (current_user.email or "") and not getattr(current_user, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Not your enrollment")
    eligible, message = await _is_refund_request_eligible(db, enrollment)
    return {"eligible": eligible, "message": message, "paid_amount": enrollment.paid_amount}


@router.get("/refund-requests", response_model=List[PortalRefundRequestOut])
async def list_refund_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalRefundRequest).order_by(TrainingPortalRefundRequest.requested_at.desc())
    is_admin = getattr(current_user, "is_super_admin", False)
    if not is_admin:
        query = query.where(TrainingPortalRefundRequest.candidate_email == (current_user.email or ""))
    if status_filter:
        query = query.where(TrainingPortalRefundRequest.status == status_filter.strip())
    result = await db.execute(query)
    return [refund_request_to_out(row) for row in result.scalars().all()]


@router.post("/refund-requests", response_model=PortalRefundRequestOut, status_code=status.HTTP_201_CREATED)
async def create_refund_request(
    body: PortalRefundRequestCreate,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == body.enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enrollment.candidate_email != (current_user.email or ""):
        raise HTTPException(status_code=403, detail="Not your enrollment")
    eligible, message = await _is_refund_request_eligible(db, enrollment)
    if not eligible:
        raise HTTPException(status_code=400, detail=message)

    amount = body.requested_amount if body.requested_amount is not None else enrollment.paid_amount
    if amount <= 0 or amount > enrollment.paid_amount:
        raise HTTPException(status_code=400, detail="Invalid refund amount")

    row = TrainingPortalRefundRequest(
        id=str(uuid.uuid4()),
        enrollment_id=enrollment.id,
        candidate_email=enrollment.candidate_email,
        candidate_name=enrollment.candidate_name,
        program_title=enrollment.title,
        requested_amount=amount,
        reason=body.reason.strip(),
        status="pending",
    )
    db.add(row)

    notif = TrainingPortalCandidateNotification(
        id=str(uuid.uuid4()),
        candidate_email=enrollment.candidate_email,
        notification_type="refund_status",
        title="Refund Request Submitted",
        description=f"Your refund request for ₹{amount:,.2f} is under review.",
        detail=body.reason.strip(),
        event_date=datetime.utcnow().strftime("%Y-%m-%d"),
        severity="info",
    )
    db.add(notif)

    await _notify_admins(
        db=db,
        notification_type="refund_request_submitted",
        title="Refund Request Submitted",
        description=f"{enrollment.candidate_name} requested a refund of ₹{amount:,.2f}.",
        detail=f"Course: {enrollment.title}. Reason: {body.reason.strip()}",
        severity="warning",
    )

    await db.commit()
    return refund_request_to_out(row)


@router.post("/refund-requests/{request_id}/resolve", response_model=PortalRefundRequestOut)
async def resolve_refund_request(
    request_id: str,
    body: PortalRefundRequestResolve,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalRefundRequest).where(TrainingPortalRefundRequest.id == request_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Request already resolved")

    enrollment_result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == row.enrollment_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    row.status = "approved" if body.action == "approve" else "rejected"
    row.admin_notes = body.admin_notes
    row.resolved_by_id = current_user.id
    row.resolved_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()

    if body.action == "approve":
        refund_body = PortalRefundRecord(
            enrollment_id=enrollment.id,
            amount=row.requested_amount,
            refund_mode=body.refund_mode,
            notes=f"Approved refund request. {body.admin_notes or ''}".strip(),
            refund_via_gateway=body.refund_via_gateway,
        )
        await record_refund(refund_body, current_user, db)

    notif = TrainingPortalCandidateNotification(
        id=str(uuid.uuid4()),
        candidate_email=row.candidate_email,
        notification_type="refund_status",
        title=f"Refund Request {row.status.title()}",
        description=(
            f"Your refund request for ₹{row.requested_amount:,.2f} was {row.status}."
            if body.action == "approve"
            else f"Your refund request was rejected. {body.admin_notes or ''}"
        ),
        event_date=datetime.utcnow().strftime("%Y-%m-%d"),
        severity="success" if body.action == "approve" else "warning",
    )
    db.add(notif)
    await db.commit()
    return refund_request_to_out(row)


# Course enrollment now goes through the token-payment seat-booking flow (see
# create_enrollment + create_payment_order/verify_payment with
# payment_purpose="token", and confirm_venue_visit) instead of an admin-reviewed
# enrollment request. The training_portal_enrollment_requests table is left in
# place (unused, with any pre-existing rows) rather than dropped.

# ── Payments ──────────────────────────────────────────────────────────────────

@router.post("/payments/create-order", response_model=PortalPaymentOrderOut)
async def create_payment_order(
    body: PortalPaymentOrderCreate,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == body.enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enrollment.candidate_email != (current_user.email or ""):
        raise HTTPException(status_code=403, detail="Not your enrollment")

    if body.payment_purpose == "token":
        # Never trust the client for the real-money token amount — always charge
        # the server-side constant, regardless of what the request body says.
        amount = settings.TRAINING_TOKEN_BOOKING_AMOUNT
    else:
        amount = body.amount if body.amount is not None else enrollment.balance_due
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Nothing to pay")

    amount_paise = int(round(amount * 100))
    rz_order = await create_razorpay_order(
        amount_paise,
        receipt=enrollment.id,
        notes={"enrollment_id": enrollment.id, "email": enrollment.candidate_email, "purpose": body.payment_purpose},
    )
    is_mock = bool(rz_order.get("mock"))

    order = TrainingPortalPaymentOrder(
        id=str(uuid.uuid4()),
        enrollment_id=enrollment.id,
        candidate_email=enrollment.candidate_email,
        amount_paise=amount_paise,
        payment_method=body.payment_method,
        payment_purpose=body.payment_purpose,
        provider_order_id=rz_order.get("id"),
        status="created",
    )
    db.add(order)
    await db.commit()

    return payment_order_to_out(
        order,
        razorpay_key_id=settings.RAZORPAY_KEY_ID if not is_mock else None,
        mock=is_mock,
    )


@router.post("/payments/verify", response_model=PortalEnrollmentOut)
async def verify_payment(
    body: PortalPaymentVerify,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    order_result = await db.execute(
        select(TrainingPortalPaymentOrder).where(TrainingPortalPaymentOrder.id == body.order_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Payment order not found")
    if order.candidate_email != (current_user.email or ""):
        raise HTTPException(status_code=403, detail="Not your payment order")

    if not verify_razorpay_signature(body.provider_order_id, body.provider_payment_id, body.provider_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    enrollment_result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == order.enrollment_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    order.provider_payment_id = body.provider_payment_id
    order.provider_signature = body.provider_signature
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    await _mark_enrollment_paid(
        db,
        enrollment,
        order.amount_paise / 100.0,
        "online",
        provider="razorpay",
        provider_transaction_id=body.provider_payment_id,
        reference_order_id=order.id,
        created_by_id=None,
    )

    if order.payment_purpose == "token":
        # A token purchase only ever books the seat / partially pays — it must
        # never fall through _mark_enrollment_paid's "fully paid" active status.
        enrollment.status = "token_booked"
        enrollment.token_amount = order.amount_paise / 100.0
        enrollment.token_paid_at = datetime.utcnow()
        enrollment.venue_visit_deadline = enrollment.token_paid_at + timedelta(days=settings.TRAINING_TOKEN_VENUE_VISIT_DAYS)

    await db.commit()

    payment_txn_result = await db.execute(
        select(TrainingPortalTransaction)
        .where(
            TrainingPortalTransaction.enrollment_id == enrollment.id,
            TrainingPortalTransaction.transaction_type == "payment",
        )
        .order_by(TrainingPortalTransaction.created_at.desc())
    )
    payment_txn = payment_txn_result.scalars().first()

    if payment_txn and order.payment_purpose == "token":
        background_tasks.add_task(
            send_training_token_booking_receipt_email,
            enrollment.candidate_email,
            enrollment.candidate_name.split(" ")[0] or enrollment.candidate_name,
            enrollment.title,
            enrollment.batch_name,
            enrollment.total_fee,
            enrollment.token_amount,
            enrollment.balance_due,
            _make_invoice_number(payment_txn.transaction_id),
            enrollment.venue_visit_deadline.strftime("%d %b %Y"),
        )
    elif payment_txn:
        background_tasks.add_task(
            send_training_portal_payment_success_email,
            enrollment.candidate_email,
            enrollment.candidate_name,
            enrollment.title,
            order.amount_paise / 100.0,
            _make_invoice_number(payment_txn.transaction_id),
            payment_txn.created_at.strftime("%d %b %Y, %I:%M %p"),
            payment_txn.payment_mode,
            payment_txn.batch_name or enrollment.batch_name,
            f"{settings.TRAINING_URL.rstrip('/')}/candidate/enrollments?invoice={payment_txn.transaction_id}",
        )
    return enrollment_to_out(enrollment)


@router.post("/payments/mock-complete", response_model=PortalEnrollmentOut)
async def mock_complete_payment(
    body: PortalPaymentOrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    """Dev/test checkout when Razorpay keys are not configured."""
    if razorpay_configured():
        raise HTTPException(status_code=400, detail="Razorpay is configured; use real checkout")

    order_out = await create_payment_order(
        PortalPaymentOrderCreate(
            enrollment_id=body.enrollment_id,
            payment_method=body.payment_method,
            amount=body.amount,
            payment_purpose=body.payment_purpose,
        ),
        current_user,
        db,
    )
    order_result = await db.execute(
        select(TrainingPortalPaymentOrder).where(TrainingPortalPaymentOrder.id == order_out.id)
    )
    order = order_result.scalar_one()
    pay_id, sig = mock_payment_ids(order.provider_order_id or order.id)
    return await verify_payment(
        PortalPaymentVerify(
            order_id=order.id,
            provider_order_id=order.provider_order_id or order.id,
            provider_payment_id=pay_id,
            provider_signature=sig,
        ),
        background_tasks,
        current_user,
        db,
    )


@router.post("/payments/webhook/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = json.loads(body.decode("utf-8"))
    payment_info = parse_webhook_payment(payload)
    if not payment_info:
        return {"status": "ignored"}

    order_result = await db.execute(
        select(TrainingPortalPaymentOrder).where(
            TrainingPortalPaymentOrder.provider_order_id == payment_info["provider_order_id"]
        )
    )
    order = order_result.scalar_one_or_none()
    if not order or order.status == "paid":
        return {"status": "ok"}

    enrollment_result = await db.execute(
        select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == order.enrollment_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        return {"status": "enrollment_missing"}

    order.provider_payment_id = payment_info["provider_payment_id"]
    order.webhook_payload = payload
    order.updated_at = datetime.utcnow()

    if payment_info.get("event") == "payment.failed":
        order.status = "failed"
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=order.candidate_email.strip().lower(),
                recipient_role="candidate",
                notification_type="payment_failed",
                title="Payment Failed",
                description="Your fee payment has failed or expired.",
                detail=f"Order ID: {order.provider_order_id or order.id}. Please retry payment from your dashboard.",
                event_date=datetime.utcnow().strftime("%Y-%m-%d"),
                severity="danger",
            )
        )
        await db.commit()
        return {"status": "failed_recorded"}

    order.status = "paid"
    order.paid_at = datetime.utcnow()
    await _mark_enrollment_paid(
        db,
        enrollment,
        order.amount_paise / 100.0,
        "online",
        provider="razorpay",
        provider_transaction_id=payment_info["provider_payment_id"],
        reference_order_id=order.id,
        created_by_id=None,
    )
    await db.commit()
    return {"status": "ok"}


@router.get("/admin/students/lookup-user", response_model=StudentLookupOut)
async def lookup_student_by_email(
    email: str = Query(..., description="Email address to lookup"),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if student user exists by email and return details for pre-filling."""
    clean_email = email.strip().lower()
    if not clean_email:
        return StudentLookupOut(exists=False)

    res = await db.execute(select(User).where(func.lower(User.email) == clean_email))
    user = res.scalar_one_or_none()
    if not user:
        return StudentLookupOut(exists=False)

    return StudentLookupOut(
        exists=True,
        user_id=str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        gender=user.gender,
        qualification=user.highest_qualification,
        address=user.address,
        preferred_job_sector=user.preferred_job_sector,
    )


@router.post("/admin/students/register-and-enroll", response_model=AdminRegisterAndEnrollStudentOut)
async def admin_register_and_enroll_student(
    body: AdminRegisterAndEnrollStudentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified endpoint for super admin to:
    1. Register a new user (with role seeker) or link existing user.
    2. Dispatch credentials via email if requested.
    3. Enroll student into course/batch.
    4. Record initial fee payment/EMI schedule & initial transaction if applicable.
    """
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Student email is required")

    # 1. Lookup or create User
    res = await db.execute(select(User).where(func.lower(User.email) == email))
    user = res.scalar_one_or_none()
    user_created = False
    credentials_sent = False

    raw_password = body.password or "Student@2026"

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            first_name=body.first_name.strip(),
            last_name=(body.last_name or "").strip(),
            email=email,
            phone=body.phone,
            hashed_password=hash_password(raw_password),
            role=UserRole.seeker,
            is_verified=True,
            onboarding_complete=True,
            gender=body.gender,
            highest_qualification=body.qualification,
            address=body.address,
        )
        db.add(user)
        await db.commit()
        user_created = True
    else:
        # Update missing profile fields on existing user if provided
        if body.first_name and not user.first_name:
            user.first_name = body.first_name.strip()
        if body.last_name and not user.last_name:
            user.last_name = body.last_name.strip()
        if body.phone and not user.phone:
            user.phone = body.phone
        if body.gender and not user.gender:
            user.gender = body.gender
        if body.qualification and not user.highest_qualification:
            user.highest_qualification = body.qualification
        if body.address and not user.address:
            user.address = body.address
        if not user.role:
            user.role = UserRole.seeker

    # Dispatch email credentials if new user or explicit send_credentials flag is true
    if body.send_credentials:
        background_tasks.add_task(
            send_welcome_email,
            email,
            user.first_name or "Student",
            "seeker",
            password=raw_password,
        )
        credentials_sent = True

    # 2. Check for active enrollment duplicate
    dup_res = await db.execute(
        select(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.candidate_email == email,
            TrainingPortalEnrollment.item_id == body.item_id,
            TrainingPortalEnrollment.status != "dropped",
        )
    )
    if dup_res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Student is already enrolled in this program")

    # 3. Batch validation
    batch_name = None
    batch_id = None
    if body.batch_id:
        batch_res = await db.execute(select(TrainingPortalBatch).where(TrainingPortalBatch.id == body.batch_id))
        batch = batch_res.scalar_one_or_none()
        if batch and batch.course_id == body.item_id:
            batch_id = batch.id
            batch_name = batch.batch_name

    # 3b. Look up course standard fee (for EMI interest/surcharge display on the receipt)
    base_fee: Optional[float] = None
    if body.enrollment_type == "course":
        course_result = await db.execute(
            select(TrainingPortalCourse).where(TrainingPortalCourse.id == body.item_id)
        )
        course = course_result.scalar_one_or_none()
        if course and course.fee:
            base_fee = float(course.fee)

    # 4. Calculate amounts
    total_fee = max(0.0, float(body.total_fee))
    paid_amount = max(0.0, float(body.paid_amount))
    paid_amount = min(paid_amount, total_fee)
    balance_due = max(0.0, total_fee - paid_amount)

    payment_status = body.payment_status
    if not payment_status:
        if balance_due <= 0.01:
            payment_status = "paid_offline"
        elif paid_amount > 0:
            payment_status = "partially_paid"
        else:
            payment_status = "pending"

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or email.split("@")[0]

    enrollment = TrainingPortalEnrollment(
        id=str(uuid.uuid4()),
        candidate_user_id=user.id,
        candidate_name=full_name,
        candidate_email=email,
        candidate_phone=user.phone,
        enrollment_type=body.enrollment_type,
        item_id=body.item_id,
        title=body.title,
        batch_id=batch_id,
        batch_name=batch_name,
        enrollment_date=today_str,
        payment_type=body.payment_type,
        payment_status=payment_status,
        payment_mode=body.payment_mode or "Cash",
        total_fee=total_fee,
        paid_amount=paid_amount,
        balance_due=balance_due,
        installments=body.installments or [],
        laptop_confirmed=body.laptop_confirmed,
        notes=body.notes,
        status="active",
    )
    db.add(enrollment)
    await db.commit()

    # 5. Create Transaction if initial payment was collected
    if paid_amount > 0:
        txn_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        txn = TrainingPortalTransaction(
            id=str(uuid.uuid4()),
            transaction_id=txn_id,
            enrollment_id=enrollment.id,
            candidate_email=email,
            candidate_name=full_name,
            program_title=body.title,
            transaction_type="offline_payment",
            amount=paid_amount,
            currency="INR",
            payment_mode=body.payment_mode or "Cash",
            status="completed",
            batch_id=batch_id,
            batch_name=batch_name,
            notes=body.notes or "Initial payment upon admin student registration",
            created_by_id=current_user.id,
        )
        db.add(txn)

        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=email,
                recipient_role="candidate",
                notification_type="payment_confirmed",
                title="Payment Confirmed",
                description=f"Your payment of ₹{paid_amount:,.2f} for {body.title} was confirmed.",
                detail=f"Payment Mode: {(body.payment_mode or 'Cash').title()}.",
                event_date=today_str,
                severity="success",
            )
        )

    # In-app notification: candidate is now enrolled and active
    db.add(
        TrainingPortalCandidateNotification(
            id=str(uuid.uuid4()),
            candidate_email=email,
            recipient_role="candidate",
            notification_type="enrollment_confirmed",
            title="Enrollment Confirmed",
            description=f"Welcome! Your enrollment in {body.title} is now active.",
            detail=(
                f"You have been assigned to batch \"{batch_name}\"."
                if batch_name
                else "Please choose a batch from your dashboard if you haven't already."
            ),
            event_date=today_str,
            severity="success",
        )
    )

    await db.commit()

    # Queue enrollment receipt email to student
    background_tasks.add_task(
        send_enrollment_receipt_email,
        email,
        user.first_name or "Student",
        body.title,
        total_fee,
        paid_amount,
        balance_due,
        payment_type=body.payment_type,
        payment_mode=body.payment_mode or "Cash",
        batch_name=batch_name,
        enrollment_date=today_str,
        installments=body.installments or [],
        password=raw_password if (user_created and body.send_credentials) else None,
        base_fee=base_fee,
    )

    return AdminRegisterAndEnrollStudentOut(
        message="Student registered and enrolled successfully",
        user_id=str(user.id),
        user_created=user_created,
        credentials_sent=credentials_sent,
        enrollment_id=enrollment.id,
        candidate_email=email,
        candidate_name=full_name,
        total_fee=total_fee,
        paid_amount=paid_amount,
        balance_due=balance_due,
        payment_status=payment_status,
    )


