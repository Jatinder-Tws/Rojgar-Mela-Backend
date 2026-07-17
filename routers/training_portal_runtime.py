import json
import logging
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status, UploadFile, File
from sqlalchemy import select, func, update, or_, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User
from models.training_portal_internship import TrainingPortalInternship
from models.training_portal_batch import TrainingPortalBatch
from models.training_portal_enrollment import TrainingPortalEnrollment
from models.training_portal_class_session import TrainingPortalClassSession
from models.training_portal_candidate_notification import TrainingPortalCandidateNotification
from models.training_portal_payment import TrainingPortalPaymentSettings, TrainingPortalPaymentOrder
from models.training_portal_transaction import TrainingPortalTransaction
from models.training_portal_refund_request import TrainingPortalRefundRequest
from models.training_portal_attendance import TrainingPortalAttendanceRecord
from models.training_portal_leave_request import TrainingPortalLeaveRequest
from models.training_portal_behavior_report import TrainingPortalBehaviorReport
from models.training_portal_course import TrainingPortalCourse
from models.training_portal_teacher import TrainingPortalTeacher
from schemas.training_portal_runtime import (
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
)
from services.auth_service import require_super_admin, require_training_portal_user
from services.training_portal_mapper import (
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
from services.training_portal_payment_service import (
    create_razorpay_order,
    create_razorpay_refund,
    verify_razorpay_signature,
    verify_webhook_signature,
    parse_webhook_payment,
    razorpay_configured,
    mock_payment_ids,
)
from services.email_service import (
    send_training_portal_batch_assigned_email,
    send_training_portal_payment_link_email,
    send_training_portal_payment_success_email,
)
from services.training_portal_class_live import (
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
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-portal/runtime", tags=["Training Portal Runtime"])

MIN_BATCH_SCHEDULE_STUDENTS = 15
MAX_BATCH_STUDENTS = 20
REFUND_REQUEST_MIN_DAYS = 14


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

    base_dir = Path(settings.UPLOAD_DIR)
    if not base_dir.is_absolute():
        base_dir = Path(__file__).parent.parent / base_dir

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
        batch_id=enrollment.batch_id,
        batch_name=enrollment.batch_name,
        notes=notes,
        created_by_id=created_by_id,
    )
    db.add(row)
    return row


def _build_invoice(
    transaction: TrainingPortalTransaction,
    enrollment: TrainingPortalEnrollment,
) -> PortalPaymentInvoiceOut:
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
        status=transaction.status,
        currency=transaction.currency,
        amount=transaction.amount,
        total_fee=enrollment.total_fee,
        paid_amount=enrollment.paid_amount,
        balance_due=enrollment.balance_due,
        enrollment_date=enrollment.enrollment_date,
        notes=transaction.notes or enrollment.notes,
        line_items=[
            PortalInvoiceLineItem(
                label=f"{transaction.program_title} ({transaction.transaction_type.title()})",
                amount=transaction.amount,
            )
        ],
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

    await db.flush()
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
    await db.flush()
    return row


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
    enrollment.paid_amount = paid_amount
    enrollment.balance_due = max(0.0, enrollment.total_fee - paid_amount)
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
    await db.flush()
    return payment_settings_to_out(row)


# ── Enrollments ───────────────────────────────────────────────────────────────

@router.get("/enrollments", response_model=List[PortalEnrollmentOut])
async def list_enrollments(
    candidate_email: Optional[str] = Query(None),
    enrollment_type: Optional[str] = Query(None, alias="type"),
    course_id: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    unassigned_only: bool = Query(False),
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

    result = await db.execute(query)
    return [enrollment_to_out(row) for row in result.scalars().all()]


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

    # Delete any stale initiated enrollments that never completed payment
    await db.execute(
        delete(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.candidate_email == email,
            TrainingPortalEnrollment.enrollment_type == body.enrollment_type,
            TrainingPortalEnrollment.item_id == body.item_id,
            TrainingPortalEnrollment.status == "payment_initiated",
        )
    )
    await db.flush()

    dup = await db.execute(
        select(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.candidate_email == email,
            TrainingPortalEnrollment.enrollment_type == body.enrollment_type,
            TrainingPortalEnrollment.item_id == body.item_id,
            TrainingPortalEnrollment.status != "dropped",
        )
    )
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

        if _is_fee_complete_from_create(body):
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
        notes=body.notes,
        status="payment_initiated" if body.payment_status == "initiated" else ("active" if body.payment_status in ("paid_online", "paid_offline", "free") else "pending"),
    )
    db.add(enrollment)
    await db.flush()

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
    await db.flush()
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

    paid = body.amount or enrollment.balance_due or enrollment.total_fee
    enrollment.paid_amount = paid
    enrollment.balance_due = max(0.0, enrollment.total_fee - paid)
    enrollment.payment_status = "paid_offline"
    enrollment.payment_mode = body.payment_mode
    enrollment.notes = body.notes or enrollment.notes or "Offline payment recorded by Admin"
    enrollment.status = "active"
    enrollment.updated_at = datetime.utcnow()
    await _try_assign_preferred_batch(db, enrollment)
    await _record_transaction(
        db,
        enrollment=enrollment,
        transaction_type="payment",
        amount=paid,
        payment_mode=body.payment_mode,
        provider="offline",
        notes=body.notes or "Offline payment recorded by Admin",
        created_by_id=current_user.id,
    )
    await db.flush()
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
    if enrollment.payment_status not in ("paid_online", "paid_offline"):
        raise HTTPException(status_code=400, detail="Enrollment has no refundable payment")
    if enrollment.paid_amount <= 0:
        raise HTTPException(status_code=400, detail="Nothing to refund")

    refund_amount = round(float(body.amount), 2)
    if refund_amount <= 0:
        raise HTTPException(status_code=400, detail="Refund amount must be greater than zero")
    if refund_amount > enrollment.paid_amount + 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Refund cannot exceed paid amount (₹{enrollment.paid_amount})",
        )

    if (
        enrollment.payment_status == "paid_online"
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

    if new_paid <= 0:
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
    await db.flush()
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

    batch = TrainingPortalBatch(
        id=str(uuid.uuid4()),
        course_id=body.course_id,
        batch_name=body.batch_name.strip(),
        instructor_id=body.instructor_id,
        instructor_name=body.instructor_name,
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
    await db.flush()

    if body.enrollment_ids:
        await _assign_enrollments_to_batch(db, batch, body.enrollment_ids, background_tasks)

    await db.flush()
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
    await db.flush()
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

    if body.batch_name is not None:
        batch.batch_name = body.batch_name.strip()
    if body.instructor_id is not None:
        batch.instructor_id = body.instructor_id
    if body.instructor_name is not None:
        batch.instructor_name = body.instructor_name.strip()
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

    await db.flush()
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
    await db.flush()


async def _lookup_teacher_email(db: AsyncSession, instructor_name: str) -> Optional[str]:
    result = await db.execute(
        select(TrainingPortalTeacher).where(
            func.lower(TrainingPortalTeacher.name) == instructor_name.strip().lower()
        )
    )
    teacher = result.scalar_one_or_none()
    return teacher.email if teacher else None


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


async def _notify_class_reminder(
    db: AsyncSession,
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
    target: date,
    tier: int = 30,
):
    if tier == 30:
        if session.reminder_sent:
            return
        session.reminder_sent = True
    elif tier == 15:
        if session.reminder_15_sent:
            return
        session.reminder_15_sent = True
    else:
        return
    session.updated_at = datetime.utcnow()

    time_label = f"{session.start_time} – {session.end_time}"
    venue = session.venue or (batch.venue if batch else "TBA")
    event_date = target.isoformat()
    detail = f"Class starts at {session.start_time}. Venue: {venue}."

    teacher_email = await _lookup_teacher_email(db, session.instructor_name)
    if teacher_email:
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=teacher_email.lower(),
                notification_type="class_reminder",
                title=f"Class in {tier} min: {session.title}",
                description=f"Your class is scheduled today at {time_label}.",
                detail=detail,
                event_date=event_date,
                severity="warning" if tier == 15 else "info",
            )
        )

    if batch:
        enrollments_result = await db.execute(
            select(TrainingPortalEnrollment).where(
                TrainingPortalEnrollment.batch_id == batch.id,
                TrainingPortalEnrollment.status != "dropped",
            )
        )
        for enrollment in enrollments_result.scalars().all():
            db.add(
                TrainingPortalCandidateNotification(
                    id=str(uuid.uuid4()),
                    candidate_email=enrollment.candidate_email,
                    notification_type="class_reminder",
                    title=f"Class in {tier} min: {session.title}",
                    description=f"Your batch class is today at {time_label}.",
                    detail=detail,
                    event_date=event_date,
                    severity="warning" if tier == 15 else "info",
                )
            )


async def _recalculate_batch_progress(db: AsyncSession, batch: TrainingPortalBatch):
    course_result = await db.execute(
        select(TrainingPortalCourse).where(TrainingPortalCourse.id == batch.course_id)
    )
    course = course_result.scalar_one_or_none()
    curriculum = (course.curriculum if course else None) or []
    total_topics = 0
    for module in curriculum:
        topics = module.get("topics") if isinstance(module, dict) else []
        total_topics += len(topics or [])

    covered = len(batch.covered_topics or [])
    completion_pct = round((covered / total_topics) * 100) if total_topics > 0 else 0

    enrollments_result = await db.execute(
        select(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.batch_id == batch.id,
            TrainingPortalEnrollment.status != "dropped",
        )
    )
    for enrollment in enrollments_result.scalars().all():
        total_result = await db.execute(
            select(func.count()).select_from(TrainingPortalAttendanceRecord).where(
                TrainingPortalAttendanceRecord.enrollment_id == enrollment.id
            )
        )
        total_marked = int(total_result.scalar() or 0)
        present_result = await db.execute(
            select(func.count()).select_from(TrainingPortalAttendanceRecord).where(
                TrainingPortalAttendanceRecord.enrollment_id == enrollment.id,
                TrainingPortalAttendanceRecord.status.in_(["present", "late", "on_leave"]),
            )
        )
        present_count = int(present_result.scalar() or 0)
        attendance_pct = round((present_count / total_marked) * 100) if total_marked > 0 else enrollment.attendance_percentage
        enrollment.attendance_percentage = attendance_pct
        enrollment.completion_percentage = completion_pct
        enrollment.updated_at = datetime.utcnow()


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


@router.post("/class-sessions", response_model=PortalClassSessionOut, status_code=status.HTTP_201_CREATED)
async def create_class_session(
    body: PortalClassSessionCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
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
    await db.flush()
    return session_to_out(session)


@router.put("/class-sessions/{session_id}", response_model=PortalClassSessionOut)
async def update_class_session(
    session_id: str,
    body: PortalClassSessionUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")

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

    updates = body.model_dump(exclude_unset=True, exclude={"admin_override"})
    for field, value in updates.items():
        setattr(session, field, value)
    session.updated_at = datetime.utcnow()
    await db.flush()
    return session_to_out(session)


@router.delete("/class-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class_session(
    session_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPortalClassSession).where(TrainingPortalClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")
    await db.delete(session)
    await db.flush()
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
        if not session_live_applies_to_date(session, today):
            if session.reminder_sent or session.reminder_15_sent:
                session.reminder_sent = False
                session.reminder_15_sent = False
                session.updated_at = now
        todays.append(session)

        if tier := pending_reminder_tier(session, now, today):
            batch = None
            if session.batch_id:
                batch_result = await db.execute(
                    select(TrainingPortalBatch).where(TrainingPortalBatch.id == session.batch_id)
                )
                batch = batch_result.scalar_one_or_none()
            await _notify_class_reminder(db, session, batch, today, tier)

    await db.flush()
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
        session.attendance_marked = False

    session.live_status = "live"
    session.live_occurrence_date = today.isoformat()
    session.started_at = now
    session.ended_at = None
    session.updated_at = now
    await db.flush()
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

    for entry in body.attendance:
        enrollment_result = await db.execute(
            select(TrainingPortalEnrollment).where(TrainingPortalEnrollment.id == entry.enrollment_id)
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if not enrollment:
            raise HTTPException(status_code=400, detail=f"Enrollment {entry.enrollment_id} not found")
        if session.batch_id and enrollment.batch_id != session.batch_id:
            raise HTTPException(status_code=400, detail="Student not in this batch")

        existing = await db.execute(
            select(TrainingPortalAttendanceRecord).where(
                TrainingPortalAttendanceRecord.class_session_id == session.id,
                TrainingPortalAttendanceRecord.enrollment_id == entry.enrollment_id,
                TrainingPortalAttendanceRecord.occurrence_date == occurrence_date,
            )
        )
        record = existing.scalar_one_or_none()
        if record:
            record.status = entry.status
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
                    status=entry.status,
                    marked_by_id=current_user.id,
                    marked_at=now,
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

    await db.flush()
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

    if candidate_email:
        query = query.where(
            TrainingPortalAttendanceRecord.candidate_email == candidate_email.strip().lower()
        )
    elif not is_admin and teacher_batch_ids is None:
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
    db.add(
        TrainingPortalCandidateNotification(
            id=str(uuid.uuid4()),
            candidate_email=email,
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
    await db.flush()
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
    await db.flush()
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
    await db.flush()
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
    await db.flush()
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
    await db.flush()
    return behavior_report_to_out(report)


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_model=List[PortalNotificationOut])
async def list_notifications(
    candidate_email: Optional[str] = Query(None),
    current_user: User = Depends(require_training_portal_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TrainingPortalCandidateNotification).order_by(
        TrainingPortalCandidateNotification.created_at.desc()
    )
    if getattr(current_user, "is_super_admin", False) and candidate_email:
        query = query.where(TrainingPortalCandidateNotification.candidate_email == candidate_email)
    else:
        query = query.where(TrainingPortalCandidateNotification.candidate_email == (current_user.email or ""))
    result = await db.execute(query)
    return [notification_to_out(row) for row in result.scalars().all()]


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
    return _build_invoice(transaction, enrollment)


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
    return _build_invoice(transaction, enrollment)


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
    await db.flush()
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
    await db.flush()
    return refund_request_to_out(row)


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

    amount = body.amount if body.amount is not None else enrollment.balance_due
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Nothing to pay")

    amount_paise = int(round(amount * 100))
    rz_order = await create_razorpay_order(
        amount_paise,
        receipt=enrollment.id,
        notes={"enrollment_id": enrollment.id, "email": enrollment.candidate_email},
    )
    is_mock = bool(rz_order.get("mock"))

    order = TrainingPortalPaymentOrder(
        id=str(uuid.uuid4()),
        enrollment_id=enrollment.id,
        candidate_email=enrollment.candidate_email,
        amount_paise=amount_paise,
        payment_method=body.payment_method,
        provider_order_id=rz_order.get("id"),
        status="created",
    )
    db.add(order)
    await db.flush()

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
    await db.flush()

    payment_txn_result = await db.execute(
        select(TrainingPortalTransaction)
        .where(
            TrainingPortalTransaction.enrollment_id == enrollment.id,
            TrainingPortalTransaction.transaction_type == "payment",
        )
        .order_by(TrainingPortalTransaction.created_at.desc())
    )
    payment_txn = payment_txn_result.scalars().first()

    if payment_txn:
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
    order.status = "paid"
    order.webhook_payload = payload
    order.paid_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
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
    await db.flush()
    return {"status": "ok"}
