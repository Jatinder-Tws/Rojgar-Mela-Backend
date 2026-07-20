"""Mappers between SQLAlchemy models and portal API schemas."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.training_portal_enrollment import TrainingPortalEnrollment
from models.training_portal_class_session import TrainingPortalClassSession
from models.training_portal_candidate_notification import TrainingPortalCandidateNotification
from models.training_portal_payment import TrainingPortalPaymentSettings, TrainingPortalPaymentOrder
from models.training_portal_transaction import TrainingPortalTransaction
from models.training_portal_refund_request import TrainingPortalRefundRequest
from models.training_portal_leave_request import TrainingPortalLeaveRequest
from models.training_portal_behavior_report import TrainingPortalBehaviorReport
from schemas.training_portal_runtime import (
    PortalEnrollmentOut,
    PortalBatchOut,
    PortalClassSessionOut,
    PortalNotificationOut,
    PortalPaymentSettingsOut,
    PortalPaymentOrderOut,
    PortalTransactionOut,
    PortalRefundRequestOut,
    PortalLeaveRequestOut,
    PortalBehaviorReportOut,
)
from services.training_portal_class_live import (
    effective_live_status,
    should_show_start_button,
    session_live_applies_to_date,
)

from models.training_portal_batch import TrainingPortalBatch


def enrollment_to_out(row: TrainingPortalEnrollment) -> PortalEnrollmentOut:
    return PortalEnrollmentOut(
        id=row.id,
        candidate_name=row.candidate_name,
        candidate_email=row.candidate_email,
        candidate_phone=row.candidate_phone,
        type=row.enrollment_type,
        item_id=row.item_id,
        batch_id=row.batch_id,
        title=row.title,
        batch_name=row.batch_name,
        enrollment_date=row.enrollment_date,
        payment_type=row.payment_type,
        payment_status=row.payment_status,
        payment_mode=row.payment_mode,
        total_fee=row.total_fee,
        paid_amount=row.paid_amount,
        balance_due=row.balance_due,
        installments=row.installments or [],
        status=row.status,
        attendance_percentage=row.attendance_percentage,
        completion_percentage=row.completion_percentage,
        is_certificate_issued=row.is_certificate_issued,
        certificate_id=row.certificate_id,
        certificate_status=row.certificate_status,
        certificate_reason=row.certificate_reason,
        voter_card_url=getattr(row, "voter_card_url", None),
        notes=row.notes,
        preferred_batch_id=getattr(row, "preferred_batch_id", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def batch_to_out(db: AsyncSession, row: TrainingPortalBatch) -> PortalBatchOut:
    seats_result = await db.execute(
        select(func.count()).select_from(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.batch_id == row.id
        )
    )
    seats_filled = int(seats_result.scalar() or 0)
    ids_result = await db.execute(
        select(TrainingPortalEnrollment.id).where(TrainingPortalEnrollment.batch_id == row.id)
    )
    enrollment_ids = [r[0] for r in ids_result.all()]
    return PortalBatchOut(
        id=row.id,
        course_id=row.course_id,
        batch_name=row.batch_name,
        instructor_id=row.instructor_id,
        instructor_name=row.instructor_name,
        start_date=row.start_date,
        end_date=row.end_date,
        days=row.days or [],
        time=row.time_slot,
        venue=row.venue,
        max_seats=row.max_seats,
        seats_filled=seats_filled,
        delivery_mode=row.delivery_mode,
        status=row.status,
        covered_topics=row.covered_topics or [],
        enrollment_ids=enrollment_ids,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def session_to_out(row: TrainingPortalClassSession) -> PortalClassSessionOut:
    return PortalClassSessionOut(
        id=row.id,
        batch_id=row.batch_id,
        item_id=row.item_id,
        title=row.title,
        instructor_name=row.instructor_name,
        date=row.date,
        start_time=row.start_time,
        end_time=row.end_time,
        days=row.days or [],
        venue=row.venue,
        note=row.note,
        schedule_type=row.schedule_type,
        postponed=row.postponed,
        teacher_unavailable=row.teacher_unavailable,
        live_status=getattr(row, "live_status", None) or "scheduled",
        live_occurrence_date=getattr(row, "live_occurrence_date", None),
        started_at=getattr(row, "started_at", None),
        ended_at=getattr(row, "ended_at", None),
        session_report=getattr(row, "session_report", None),
        covered_topic_ids=getattr(row, "covered_topic_ids", None) or [],
        attachment_url=getattr(row, "attachment_url", None),
        attachment_filename=getattr(row, "attachment_filename", None),
        reminder_sent=bool(getattr(row, "reminder_sent", False)),
        reminder_15_sent=bool(getattr(row, "reminder_15_sent", False)),
        end_reminder_sent=bool(getattr(row, "end_reminder_sent", False)),
        late_start_reason=getattr(row, "late_start_reason", None),
        early_end_reason=getattr(row, "early_end_reason", None),
        attendance_marked=bool(getattr(row, "attendance_marked", False)),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def session_to_out_for_date(
    row: TrainingPortalClassSession,
    target: date,
    now: Optional[datetime] = None,
) -> PortalClassSessionOut:
    from services.training_portal_class_live import now_ist

    current = now or now_ist()
    effective = effective_live_status(row, current, target)
    applies = session_live_applies_to_date(row, target)
    base = session_to_out(row)
    return base.model_copy(
        update={
            "live_status": effective,
            "occurrence_date": target.isoformat(),
            "can_start": should_show_start_button(row, current, target),
            "started_at": getattr(row, "started_at", None) if applies and effective in {"live", "completed"} else None,
            "ended_at": getattr(row, "ended_at", None) if applies and effective == "completed" else None,
            "session_report": getattr(row, "session_report", None) if applies and effective == "completed" else None,
            "covered_topic_ids": (getattr(row, "covered_topic_ids", None) or []) if applies and effective == "completed" else [],
            "attachment_url": getattr(row, "attachment_url", None) if applies and effective == "completed" else None,
            "attachment_filename": getattr(row, "attachment_filename", None) if applies and effective == "completed" else None,
            "late_start_reason": getattr(row, "late_start_reason", None) if applies and effective in {"live", "completed"} else None,
            "early_end_reason": getattr(row, "early_end_reason", None) if applies and effective == "completed" else None,
            "attendance_marked": bool(getattr(row, "attendance_marked", False)) and applies and effective == "completed",
        }
    )


def notification_to_out(row: TrainingPortalCandidateNotification) -> PortalNotificationOut:
    return PortalNotificationOut(
        id=row.id,
        candidate_email=row.candidate_email,
        recipient_role=row.recipient_role,
        is_read=row.is_read,
        type=row.notification_type,
        title=row.title,
        description=row.description,
        detail=row.detail,
        date=row.event_date,
        severity=row.severity,
        created_at=row.created_at,
    )



def payment_settings_to_out(row: TrainingPortalPaymentSettings) -> PortalPaymentSettingsOut:
    return PortalPaymentSettingsOut(
        upi=row.upi,
        card=row.card,
        emi=row.emi,
        offline=row.offline,
        email=row.email,
        updated_at=row.updated_at,
    )


def payment_order_to_out(row: TrainingPortalPaymentOrder, razorpay_key_id: str | None = None, mock: bool = False) -> PortalPaymentOrderOut:
    return PortalPaymentOrderOut(
        id=row.id,
        enrollment_id=row.enrollment_id,
        amount=row.amount_paise / 100.0,
        currency=row.currency,
        payment_method=row.payment_method,
        status=row.status,
        provider=row.provider,
        provider_order_id=row.provider_order_id,
        razorpay_key_id=razorpay_key_id,
        mock_checkout=mock,
    )


def transaction_to_out(row: TrainingPortalTransaction) -> PortalTransactionOut:
    return PortalTransactionOut(
        id=row.id,
        transaction_id=row.transaction_id,
        enrollment_id=row.enrollment_id,
        candidate_email=row.candidate_email,
        candidate_name=row.candidate_name,
        program_title=row.program_title,
        transaction_type=row.transaction_type,
        amount=row.amount,
        currency=row.currency,
        payment_mode=row.payment_mode,
        status=row.status,
        provider=row.provider,
        provider_transaction_id=row.provider_transaction_id,
        reference_order_id=row.reference_order_id,
        batch_id=row.batch_id,
        batch_name=row.batch_name,
        notes=row.notes,
        created_at=row.created_at,
    )


def refund_request_to_out(row: TrainingPortalRefundRequest) -> PortalRefundRequestOut:
    return PortalRefundRequestOut(
        id=row.id,
        enrollment_id=row.enrollment_id,
        candidate_email=row.candidate_email,
        candidate_name=row.candidate_name,
        program_title=row.program_title,
        requested_amount=row.requested_amount,
        reason=row.reason,
        status=row.status,
        admin_notes=row.admin_notes,
        requested_at=row.requested_at,
        resolved_at=row.resolved_at,
        created_at=row.created_at,
    )


def leave_to_out(row: TrainingPortalLeaveRequest) -> PortalLeaveRequestOut:
    return PortalLeaveRequestOut(
        id=row.id,
        requester_type=row.requester_type,
        candidate_email=row.candidate_email,
        candidate_name=row.candidate_name,
        teacher_email=row.teacher_email,
        teacher_name=row.teacher_name,
        session_id=row.session_id,
        date=row.date,
        batch_id=row.batch_id,
        batch_name=row.batch_name,
        reason=row.reason,
        status=row.status,
        reviewed_by_role=row.reviewed_by_role,
        review_note=row.review_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def behavior_report_to_out(row: TrainingPortalBehaviorReport) -> PortalBehaviorReportOut:
    return PortalBehaviorReportOut(
        id=row.id,
        enrollment_id=row.enrollment_id,
        candidate_name=row.candidate_name,
        candidate_email=row.candidate_email,
        batch_id=row.batch_id,
        batch_name=row.batch_name,
        instructor_id=row.instructor_id,
        instructor_name=row.instructor_name,
        teacher_email=row.teacher_email,
        date=row.report_date,
        discipline_rating=row.discipline_rating,
        participation_rating=row.participation_rating,
        performance_rating=row.performance_rating,
        comments=row.comments,
        flagged_for_review=row.flagged_for_review,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
