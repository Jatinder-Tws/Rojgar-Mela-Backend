"""
Live class lifecycle: start reminders and 15-min end reminders.

Does not auto-complete live classes — teachers/admins must end manually
so attendance and notes/MOM can be submitted.

Runs from:
  - GET /class-sessions/today (immediate UX while a user is online)
  - Periodic Celery Beat (works even when nobody is polling)
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.training_portal.models.training_portal_attendance import TrainingPortalAttendanceRecord
from app.modules.training_portal.models.training_portal_batch import TrainingPortalBatch
from app.modules.training_portal.models.training_portal_candidate_notification import TrainingPortalCandidateNotification
from app.modules.training_portal.models.training_portal_class_session import TrainingPortalClassSession
from app.modules.training_portal.models.training_portal_course import TrainingPortalCourse
from app.modules.training_portal.models.training_portal_enrollment import TrainingPortalEnrollment
from app.modules.training_portal.models.training_portal_leave_request import TrainingPortalLeaveRequest
from app.modules.training_portal.models.training_portal_teacher import TrainingPortalTeacher
from app.modules.training_portal.services.training_portal_class_live import (
    effective_live_status,
    now_ist,
    pending_reminder_tier,
    session_end_datetime,
    session_live_applies_to_date,
    session_occurs_on_date,
    today_ist,
)

logger = logging.getLogger(__name__)

END_REMINDER_MINUTES = 15


async def _lookup_teacher_email(db: AsyncSession, instructor_name: str) -> Optional[str]:
    result = await db.execute(
        select(TrainingPortalTeacher).where(
            func.lower(TrainingPortalTeacher.name) == instructor_name.strip().lower()
        )
    )
    teacher = result.scalar_one_or_none()
    return teacher.email if teacher else None


async def _load_batch(db: AsyncSession, batch_id: Optional[str]) -> Optional[TrainingPortalBatch]:
    if not batch_id:
        return None
    result = await db.execute(
        select(TrainingPortalBatch).where(TrainingPortalBatch.id == batch_id)
    )
    return result.scalar_one_or_none()


async def recalculate_batch_progress(db: AsyncSession, batch: TrainingPortalBatch) -> None:
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
        attendance_pct = (
            round((present_count / total_marked) * 100)
            if total_marked > 0
            else enrollment.attendance_percentage
        )
        enrollment.attendance_percentage = attendance_pct
        enrollment.completion_percentage = completion_pct
        enrollment.updated_at = datetime.utcnow()


async def notify_class_reminder(
    db: AsyncSession,
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
    target: date,
    tier: int = 30,
) -> None:
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
                recipient_role="teacher",
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
                    recipient_role="candidate",
                    notification_type="class_reminder",
                    title=f"Class in {tier} min: {session.title}",
                    description=f"Your batch class is today at {time_label}.",
                    detail=detail,
                    event_date=event_date,
                    severity="warning" if tier == 15 else "info",
                )
            )


async def notify_class_ending_soon(
    db: AsyncSession,
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
    target: date,
) -> None:
    if getattr(session, "end_reminder_sent", False):
        return
    session.end_reminder_sent = True
    session.updated_at = datetime.utcnow()

    event_date = target.isoformat()
    detail = "This class session will close automatically in 15 minutes."

    teacher_email = await _lookup_teacher_email(db, session.instructor_name)
    if teacher_email:
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=teacher_email.lower(),
                recipient_role="teacher",
                notification_type="class_reminder",
                title=f"Class ending soon: {session.title}",
                description=f"Your live class will end automatically at {session.end_time} (in 15 minutes).",
                detail=detail,
                event_date=event_date,
                severity="warning",
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
                    recipient_role="candidate",
                    notification_type="class_reminder",
                    title=f"Class ending soon: {session.title}",
                    description=f"Your live class will end automatically at {session.end_time} (in 15 minutes).",
                    detail=detail,
                    event_date=event_date,
                    severity="warning",
                )
            )


async def notify_class_ended_automatically(
    db: AsyncSession,
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
    target: date,
) -> None:
    event_date = target.isoformat()
    detail = "This class session was completed automatically as it exceeded its scheduled duration."

    teacher_email = await _lookup_teacher_email(db, session.instructor_name)
    if teacher_email:
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=teacher_email.lower(),
                recipient_role="teacher",
                notification_type="class_reminder",
                title=f"Class ended automatically: {session.title}",
                description=f"Your class has automatically closed as the scheduled time ({session.end_time}) was reached.",
                detail=detail,
                event_date=event_date,
                severity="info",
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
                    recipient_role="candidate",
                    notification_type="class_reminder",
                    title=f"Class ended automatically: {session.title}",
                    description=f"Your class has automatically closed as the scheduled time ({session.end_time}) was reached.",
                    detail=detail,
                    event_date=event_date,
                    severity="info",
                )
            )


async def auto_end_live_session(
    db: AsyncSession,
    session: TrainingPortalClassSession,
    batch: Optional[TrainingPortalBatch],
    occurrence_date: date,
) -> None:
    """Mark a live session completed and create default attendance + notifications."""
    if (session.live_status or "").strip().lower() != "live":
        return

    now = now_ist()
    session.live_status = "completed"
    session.ended_at = now
    session.attendance_marked = True
    if not (session.session_report or "").strip():
        session.session_report = "Class ended automatically after scheduled duration."
    session.updated_at = datetime.utcnow()

    if batch:
        occurrence = occurrence_date.isoformat()
        enrollments_result = await db.execute(
            select(TrainingPortalEnrollment).where(
                TrainingPortalEnrollment.batch_id == batch.id,
                TrainingPortalEnrollment.status != "dropped",
            )
        )
        enrollments = enrollments_result.scalars().all()
        for enrollment in enrollments:
            leave_result = await db.execute(
                select(TrainingPortalLeaveRequest).where(
                    TrainingPortalLeaveRequest.requester_type == "student",
                    TrainingPortalLeaveRequest.candidate_email == enrollment.candidate_email.lower(),
                    TrainingPortalLeaveRequest.batch_id == batch.id,
                    TrainingPortalLeaveRequest.date == occurrence,
                    TrainingPortalLeaveRequest.status == "approved",
                )
            )
            approved_leave = leave_result.scalar_one_or_none()
            status_to_mark = "on_leave" if approved_leave else "present"

            existing = await db.execute(
                select(TrainingPortalAttendanceRecord).where(
                    TrainingPortalAttendanceRecord.class_session_id == session.id,
                    TrainingPortalAttendanceRecord.enrollment_id == enrollment.id,
                    TrainingPortalAttendanceRecord.occurrence_date == occurrence,
                )
            )
            record = existing.scalar_one_or_none()
            if record:
                record.status = status_to_mark
                record.marked_at = datetime.utcnow()
            else:
                db.add(
                    TrainingPortalAttendanceRecord(
                        id=str(uuid.uuid4()),
                        class_session_id=session.id,
                        enrollment_id=enrollment.id,
                        occurrence_date=occurrence,
                        batch_id=batch.id,
                        candidate_email=enrollment.candidate_email,
                        candidate_name=enrollment.candidate_name,
                        status=status_to_mark,
                        marked_at=datetime.utcnow(),
                    )
                )
        await recalculate_batch_progress(db, batch)

    await notify_class_ended_automatically(db, session, batch, occurrence_date)
    logger.info(
        "[CLASS LIFECYCLE] Auto-ended session %s (%s) at scheduled end %s",
        session.id,
        session.title,
        session.end_time,
    )


def _occurrence_date_for_live_session(session: TrainingPortalClassSession) -> date:
    occ_str = (getattr(session, "live_occurrence_date", None) or "").strip()
    if occ_str:
        try:
            return date.fromisoformat(occ_str)
        except ValueError:
            pass
    return today_ist()


async def process_live_session_end_lifecycle(
    db: AsyncSession,
    session: TrainingPortalClassSession,
    now: Optional[datetime] = None,
) -> None:
    """Send ending-soon reminder when approaching scheduled end_time.

    Does NOT auto-complete the class — the teacher/admin must end it manually
    so they can mark attendance and add notes/MOM.
    """
    if (session.live_status or "").strip().lower() != "live":
        return

    now = now or now_ist()
    occurrence_date = _occurrence_date_for_live_session(session)
    end_dt = session_end_datetime(session, occurrence_date)
    if not end_dt:
        # Fallback: if end time cannot be parsed, use 2h after started_at for reminder only.
        started = getattr(session, "started_at", None)
        if not started:
            return
        end_dt = started + timedelta(hours=2)

    minutes_remaining = (end_dt - now).total_seconds() / 60.0
    batch = await _load_batch(db, session.batch_id)

    if 0 < minutes_remaining <= END_REMINDER_MINUTES:
        await notify_class_ending_soon(db, session, batch, occurrence_date)
    # Past end time: leave session live. UI shows an end-due alert for manual complete.

async def process_session_start_reminders(
    db: AsyncSession,
    session: TrainingPortalClassSession,
    target: date,
    now: Optional[datetime] = None,
) -> None:
    now = now or now_ist()
    if not session_occurs_on_date(session, target):
        return
    if not session_live_applies_to_date(session, target):
        if session.reminder_sent or session.reminder_15_sent or getattr(session, "end_reminder_sent", False):
            session.reminder_sent = False
            session.reminder_15_sent = False
            session.end_reminder_sent = False
            session.updated_at = now

    tier = pending_reminder_tier(session, now, target)
    if not tier:
        return
    batch = await _load_batch(db, session.batch_id)
    await notify_class_reminder(db, session, batch, target, tier)


async def process_todays_session_lifecycle(
    db: AsyncSession,
    session: TrainingPortalClassSession,
    target: Optional[date] = None,
    now: Optional[datetime] = None,
) -> None:
    """Lifecycle hooks used by GET /class-sessions/today for a single session."""
    target = target or today_ist()
    now = now or now_ist()

    if not session_occurs_on_date(session, target):
        return

    await process_session_start_reminders(db, session, target, now)

    live_status = effective_live_status(session, now, target)
    if live_status == "live":
        await process_live_session_end_lifecycle(db, session, now)


async def process_all_class_lifecycles(db: AsyncSession) -> dict[str, int]:
    """
    Periodic sweep:
      1) All DB-live sessions → ending-soon reminders (no auto-end)
      2) Today's scheduled sessions → 30/15 min start reminders
    """
    from app.modules.training_portal.services.class_live_realtime import build_class_live_event

    now = now_ist()
    today = today_ist()
    ended = 0
    end_reminders = 0
    start_reminders = 0
    live_events: list[dict] = []

    live_result = await db.execute(
        select(TrainingPortalClassSession).where(
            TrainingPortalClassSession.live_status == "live"
        )
    )
    live_sessions = list(live_result.scalars().all())
    for session in live_sessions:
        before_end_flag = bool(getattr(session, "end_reminder_sent", False))
        await process_live_session_end_lifecycle(db, session, now)
        if not before_end_flag and bool(getattr(session, "end_reminder_sent", False)):
            end_reminders += 1
            live_events.append(build_class_live_event(session, "ending_soon"))

    today_result = await db.execute(select(TrainingPortalClassSession))
    for session in today_result.scalars().all():
        if not session_occurs_on_date(session, today):
            continue
        before_30 = bool(session.reminder_sent)
        before_15 = bool(session.reminder_15_sent)
        await process_session_start_reminders(db, session, today, now)
        if (not before_30 and session.reminder_sent) or (not before_15 and session.reminder_15_sent):
            start_reminders += 1

    await db.flush()
    return {
        "live_checked": len(live_sessions),
        "auto_ended": ended,
        "end_reminders": end_reminders,
        "start_reminders": start_reminders,
        "_live_events": live_events,
    }


update_class_lifecycles = process_all_class_lifecycles


async def process_expired_token_visits(db: AsyncSession) -> dict[str, int]:
    """
    Daily sweep: any token-booked seat whose 5-day venue-visit deadline has passed
    without SuperAdmin confirmation is marked non-refundable and the candidate is notified.
    Idempotent — the `token_expired` guard means already-processed rows are skipped on rerun.
    """
    from app.shared.services.email_service import send_seat_cancellation_email

    now = datetime.utcnow()
    result = await db.execute(
        select(TrainingPortalEnrollment).where(
            TrainingPortalEnrollment.status == "token_booked",
            TrainingPortalEnrollment.token_expired.is_(False),
            TrainingPortalEnrollment.venue_visit_deadline.isnot(None),
            TrainingPortalEnrollment.venue_visit_deadline < now,
        )
    )
    expired = list(result.scalars().all())

    for enrollment in expired:
        enrollment.token_expired = True
        enrollment.updated_at = now
        db.add(
            TrainingPortalCandidateNotification(
                id=str(uuid.uuid4()),
                candidate_email=enrollment.candidate_email,
                recipient_role="candidate",
                notification_type="token_expired",
                title="Seat Booking Cancelled",
                description=f"Your seat booking for {enrollment.title} was cancelled due to non-appearance.",
                detail="Your token payment is non-refundable as you did not visit the venue within 5 days.",
                event_date=now.strftime("%Y-%m-%d"),
                severity="warning",
            )
        )
        try:
            await send_seat_cancellation_email(
                enrollment.candidate_email,
                enrollment.candidate_name,
                enrollment.title,
                enrollment.batch_name,
            )
        except Exception as exc:  # pragma: no cover - best-effort notification
            logger.error(f"Failed to send seat cancellation email to {enrollment.candidate_email}: {exc}")

    await db.flush()
    return {"expired_token_bookings": len(expired)}
