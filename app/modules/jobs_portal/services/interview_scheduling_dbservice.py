from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import delete, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.modules.jobs_portal.models.application import Application, ApplicationStatus
from app.modules.jobs_portal.models.interview import Interview, InterviewSource, InterviewStatus, InterviewType
from app.modules.jobs_portal.models.provider_availability_window import ProviderAvailabilityWindow
from app.modules.jobs_portal.models.provider_interview_settings import ProviderInterviewSettings
from app.shared.models.user import User
from app.modules.jobs_portal.models.job import JobPosting
from app.shared.models.notification import NotificationType
from app.shared.services.notification_service import create_notification
from app.shared.services.audit_service import log_audit_event
from app.modules.jobs_portal.schemas.interviews import (
    INTERVIEW_REASON_LABELS,
    InterviewCreate,
    InterviewOut,
    InterviewOutcomeUpdate,
    InterviewReschedule,
)
from app.modules.jobs_portal.schemas.interview_scheduling import ProviderInterviewSettingsUpdate
from app.modules.jobs_portal.services.interview_flow import auto_schedule_block_reason

logger = logging.getLogger(__name__)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def format_outcome_notes(
    reason_code: Optional[str],
    notes: Optional[str],
) -> Optional[str]:
    """Combine structured reason + free-text notes for storage/display."""
    parts: List[str] = []
    if reason_code:
        parts.append(INTERVIEW_REASON_LABELS.get(reason_code, reason_code))
    note = (notes or "").strip()
    if note:
        parts.append(note)
    if not parts:
        return None
    return ". ".join(parts)


async def _interview_out(
    interview: Interview,
    provider: User,
    job_title: Optional[str] = None,
    seeker_name: Optional[str] = None,
) -> InterviewOut:
    item = InterviewOut.model_validate(interview)
    if job_title is not None:
        item.job_title = job_title
    if seeker_name is not None:
        item.seeker_name = seeker_name
    item.provider_name = f"{provider.first_name} {provider.last_name}".strip() or None
    return item


async def get_or_create_settings(
    db: AsyncSession,
    provider_id: str,
) -> ProviderInterviewSettings:
    result = await db.execute(
        select(ProviderInterviewSettings)
        .where(ProviderInterviewSettings.provider_id == provider_id)
        .options(
            selectinload(ProviderInterviewSettings.availability_windows)
        )
    )

    settings = result.scalar_one_or_none()

    if not settings:
        settings = ProviderInterviewSettings(provider_id=provider_id, timezone="Asia/Kolkata")
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        settings.availability_windows = []

    return settings


def _reject_incomplete_auto_schedule(
    settings: ProviderInterviewSettings,
    has_windows: Optional[bool] = None,
) -> None:
    if not settings.auto_schedule_enabled:
        return
    windows_ready = (
        bool(settings.availability_windows) if has_windows is None else has_windows
    )
    reason = auto_schedule_block_reason(
        settings.default_interview_type,
        settings.default_meeting_link,
        settings.default_location,
        windows_ready,
    )
    if reason:
        raise HTTPException(status_code=400, detail=reason)


async def upsert_settings(
    db: AsyncSession,
    provider_id: str,
    body: ProviderInterviewSettingsUpdate,
) -> ProviderInterviewSettings:
    settings = await get_or_create_settings(db, provider_id)
    data = body.model_dump(exclude_unset=True, exclude={"windows"})

    for key, value in data.items():
        setattr(settings, key, value)

    has_windows: Optional[bool] = None
    if body.windows is not None:
        has_windows = len(body.windows) > 0
        await db.execute(
            delete(ProviderAvailabilityWindow).where(
                ProviderAvailabilityWindow.provider_id == provider_id
            )
        )
        for window in body.windows:
            db.add(
                ProviderAvailabilityWindow(
                    provider_id=provider_id,
                    day_of_week=window.day_of_week,
                    start_time=window.start_time,
                    end_time=window.end_time,
                    start_period=window.start_period,
                    end_period=window.end_period
                )
            )

    settings.updated_at = _utc_now_naive()
    _reject_incomplete_auto_schedule(settings, has_windows=has_windows)
    await db.commit()
    return settings


async def toggle_auto_schedule_db(
    db: AsyncSession,
    provider_id: str,
    auto_schedule_enabled: bool,
) -> ProviderInterviewSettings:
    settings = await get_or_create_settings(db, provider_id)
    if auto_schedule_enabled:
        settings.auto_schedule_enabled = True
        _reject_incomplete_auto_schedule(settings)
    else:
        settings.auto_schedule_enabled = False
    await db.commit()
    return settings


async def load_busy_intervals(
    db: AsyncSession,
    provider_id: str,
    start_utc: datetime,
    end_utc: datetime,
    slot_duration_minutes: int,
    exclude_interview_id: Optional[str] = None,
) -> List[Tuple[datetime, datetime]]:
    q = select(Interview.scheduled_at).where(
        Interview.provider_id == provider_id,
        Interview.status == InterviewStatus.scheduled,
        Interview.scheduled_at >= start_utc,
        Interview.scheduled_at < end_utc,
    )
    if exclude_interview_id:
        q = q.where(Interview.id != exclude_interview_id)
    result = await db.execute(q)
    duration = timedelta(minutes=slot_duration_minutes)
    return [
        (row[0], row[0] + duration)
        for row in result.all()
    ]


async def create_interview(
    db: AsyncSession,
    body: InterviewCreate,
    provider: User,
) -> InterviewOut:
    # Validation: Prevent past scheduling (naive UTC vs aware ISO both OK)
    if _to_utc_naive(body.scheduled_at) < _utc_now_naive():
        raise HTTPException(
            status_code=400, 
            detail="Cannot schedule an interview in the past"
        )

    # Verify job exists and belongs to provider
    job_result = await db.execute(
        select(JobPosting).where(JobPosting.id == body.job_id, JobPosting.provider_id == provider.id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not body.application_id:
        raise HTTPException(status_code=400, detail="application_id is required")

    app_result = await db.execute(select(Application).where(Application.id == body.application_id))
    application = app_result.scalar_one_or_none()
    if (
        not application
        or str(application.job_id) != str(body.job_id)
        or not application.seeker_id
        or str(application.seeker_id) != str(body.seeker_id)
    ):
        raise HTTPException(
            status_code=400,
            detail="Application does not match this job and candidate",
        )
    if application.status not in (ApplicationStatus.shortlisted, ApplicationStatus.interviewing):
        raise HTTPException(
            status_code=409,
            detail="Shortlist the candidate before scheduling an interview",
        )

    existing_result = await db.execute(
        select(Interview.id).where(
            Interview.application_id == application.id,
            Interview.status.in_([InterviewStatus.scheduled, InterviewStatus.completed]),
        )
    )
    if existing_result.first():
        raise HTTPException(
            status_code=409,
            detail="An interview already exists for this application",
        )

    # Import locally to avoid circular import issues
    from app.modules.jobs_portal.services.interview_scheduling_service import assert_slot_available

    settings = await get_or_create_settings(db, provider.id)
    scheduled_at = _to_utc_naive(body.scheduled_at)
    await assert_slot_available(
        db, provider.id, scheduled_at, settings.slot_duration_minutes
    )

    interview_type = InterviewType(body.interview_type) if body.interview_type else InterviewType.video
    if interview_type == InterviewType.video and not body.meeting_link:
        raise HTTPException(status_code=400, detail="Meeting link is required for video interviews")
    if interview_type == InterviewType.walk_in and not body.location:
        raise HTTPException(status_code=400, detail="Location is required for walk-in interviews")

    interview = Interview(
        seeker_id=body.seeker_id,
        provider_id=provider.id,
        job_id=body.job_id,
        application_id=body.application_id,
        title=body.title,
        interviewer_name=body.interviewer_name,
        agenda=body.agenda,
        interview_type=interview_type,
        meeting_link=body.meeting_link,
        location=body.location,
        status=InterviewStatus.scheduled,
        scheduled_at=scheduled_at,
        scheduled_period=body.scheduled_period,
        source=InterviewSource.manual,
    )
    db.add(interview)

    application.status = ApplicationStatus.interviewing

    await db.flush()
    await log_audit_event(
        db,
        provider,
        action="CREATE",
        entity_type="interview",
        entity_id=str(interview.id),
        entity_name=interview.title or job.title,
        description=f"Scheduled interview for '{job.title}'",
        changes={"application_id": str(application.id), "scheduled_at": scheduled_at.isoformat()},
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(interview)

    await create_notification(
        db=db,
        user_id=body.seeker_id,
        type=NotificationType.match,
        title="Interview Scheduled",
        message=(
            f"{provider.first_name} has scheduled an interview for '{job.title}'. "
            "Open your dashboard to see the date and time in your timezone."
        ),
        related_job_id=body.job_id,
        related_user_id=str(provider.id),
        auto_commit=True,
    )

    seeker_result = await db.execute(
        select(User.first_name, User.last_name, User.email).where(User.id == body.seeker_id)
    )
    seeker_data = seeker_result.first()
    s_fn, s_ln, s_email = (
        (seeker_data.first_name, seeker_data.last_name, seeker_data.email)
        if seeker_data
        else ("Unknown", "User", None)
    )

    if s_email:
        try:
            from app.shared.services.celery_tasks import queue_interview_scheduled_email

            queue_interview_scheduled_email(
                to_email=s_email,
                seeker_name=s_fn or "there",
                job_title=job.title,
                company_name=provider.company_name
                or f"{provider.first_name or ''} {provider.last_name or ''}".strip(),
                scheduled_at=scheduled_at.isoformat()
                if hasattr(scheduled_at, "isoformat")
                else str(scheduled_at),
                interview_type=body.interview_type or "video",
                meeting_link=body.meeting_link,
                location=body.location,
                agenda=body.agenda,
                scheduled_period=body.scheduled_period,
                interviewer_name=body.interviewer_name,
            )
        except Exception:
            logger.exception("Failed to queue interview scheduled email to %s", s_email)

    res = InterviewOut.model_validate(interview)
    res.job_title = job.title
    res.seeker_name = f"{s_fn} {s_ln}"
    res.provider_name = f"{provider.first_name} {provider.last_name}"
    
    return res


async def get_user_interviews(
    db: AsyncSession,
    user: User,
) -> List[InterviewOut]:
    from sqlalchemy.orm import joinedload

    query = (
        select(Interview)
        .options(
            joinedload(Interview.job),
            joinedload(Interview.seeker),
            joinedload(Interview.provider),
        )
        .where(or_(Interview.seeker_id == user.id, Interview.provider_id == user.id))
        .order_by(Interview.scheduled_at.desc())
    )
    result = await db.execute(query)
    interviews = result.scalars().all()
    
    out = []
    for i in interviews:
        item = InterviewOut.model_validate(i)
        item.job_title = i.job.title if i.job else "Unknown Job"
        item.seeker_name = f"{i.seeker.first_name} {i.seeker.last_name}" if i.seeker else "Unknown Seeker"
        company = (i.provider.company_name or "").strip() if i.provider else ""
        person = f"{i.provider.first_name} {i.provider.last_name}".strip() if i.provider else ""
        item.company_name = company or None
        item.provider_name = company or person or "Unknown Provider"
        out.append(item)
        
    return out


async def _require_provider_scheduled_interview(
    db: AsyncSession,
    interview_id: str,
    provider: User,
) -> Interview:
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if interview.provider_id != provider.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if interview.status != InterviewStatus.scheduled:
        raise HTTPException(
            status_code=409,
            detail=f"Interview is already {interview.status.value}",
        )
    return interview


async def reschedule_interview(
    db: AsyncSession,
    interview_id: str,
    body: InterviewReschedule,
    provider: User,
) -> InterviewOut:
    interview = await _require_provider_scheduled_interview(db, interview_id, provider)
    scheduled_at = _to_utc_naive(body.scheduled_at)
    if scheduled_at < _utc_now_naive():
        raise HTTPException(status_code=400, detail="Cannot reschedule an interview to the past")

    from app.modules.jobs_portal.services.interview_scheduling_service import assert_slot_available

    settings = await get_or_create_settings(db, provider.id)
    await assert_slot_available(
        db,
        provider.id,
        scheduled_at,
        settings.slot_duration_minutes,
        exclude_interview_id=str(interview.id),
    )

    if interview.interview_type == InterviewType.video:
        link = (body.meeting_link if body.meeting_link is not None else interview.meeting_link) or ""
        if not str(link).strip():
            raise HTTPException(status_code=400, detail="Meeting link is required for video interviews")
        interview.meeting_link = str(link).strip()
    if interview.interview_type == InterviewType.walk_in:
        loc = (body.location if body.location is not None else interview.location) or ""
        if not str(loc).strip():
            raise HTTPException(status_code=400, detail="Location is required for walk-in interviews")
        interview.location = str(loc).strip()

    previous_at = interview.scheduled_at
    interview.scheduled_at = scheduled_at
    if body.scheduled_period is not None:
        interview.scheduled_period = body.scheduled_period
    if body.notes and body.notes.strip():
        interview.outcome_notes = body.notes.strip()
    interview.updated_at = _utc_now_naive()

    await log_audit_event(
        db,
        provider,
        action="UPDATE",
        entity_type="interview",
        entity_id=str(interview.id),
        entity_name=interview.title,
        description=f"Rescheduled interview '{interview.title}'",
        changes={
            "previous_scheduled_at": previous_at.isoformat() if previous_at else None,
            "scheduled_at": scheduled_at.isoformat(),
        },
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(interview)

    job_res = await db.execute(select(JobPosting.title).where(JobPosting.id == interview.job_id))
    job_title = job_res.scalar() or "this role"
    await create_notification(
        db=db,
        user_id=interview.seeker_id,
        type=NotificationType.match,
        title="Interview Rescheduled",
        message=(
            f"{provider.first_name or 'The recruiter'} rescheduled your interview for '{job_title}'. "
            "Open your dashboard to see the new date and time."
        ),
        related_job_id=str(interview.job_id),
        related_user_id=str(provider.id),
        auto_commit=True,
    )

    seeker_res = await db.execute(
        select(User.first_name, User.last_name, User.email).where(User.id == interview.seeker_id)
    )
    seeker_data = seeker_res.first()
    s_fn = seeker_data.first_name if seeker_data else "Unknown"
    s_ln = seeker_data.last_name if seeker_data else "User"
    s_email = seeker_data.email if seeker_data else None
    if s_email:
        try:
            from app.shared.services.celery_tasks import queue_interview_scheduled_email

            queue_interview_scheduled_email(
                to_email=s_email,
                seeker_name=s_fn or "there",
                job_title=job_title,
                company_name=provider.company_name
                or f"{provider.first_name or ''} {provider.last_name or ''}".strip(),
                scheduled_at=scheduled_at.isoformat(),
                interview_type=interview.interview_type.value
                if hasattr(interview.interview_type, "value")
                else str(interview.interview_type),
                meeting_link=interview.meeting_link,
                location=interview.location,
                agenda=interview.agenda,
                scheduled_period=interview.scheduled_period,
                interviewer_name=interview.interviewer_name,
            )
        except Exception:
            logger.exception("Failed to queue interview reschedule email to %s", s_email)

    return await _interview_out(interview, provider, job_title=job_title, seeker_name=f"{s_fn} {s_ln}")


async def record_interview_outcome(
    db: AsyncSession,
    interview_id: str,
    body: InterviewOutcomeUpdate,
    provider: User,
) -> InterviewOut:
    interview = await _require_provider_scheduled_interview(db, interview_id, provider)

    outcome_notes = format_outcome_notes(body.reason_code, body.notes)
    if body.outcome in ("no_show", "cancelled", "rejected") and not outcome_notes:
        raise HTTPException(
            status_code=400,
            detail="Please provide a reason or notes for this outcome",
        )

    if body.outcome == "selected":
        interview.status = InterviewStatus.completed
    elif body.outcome == "rejected":
        interview.status = InterviewStatus.completed
    elif body.outcome == "no_show":
        interview.status = InterviewStatus.no_show
    else:
        interview.status = InterviewStatus.cancelled

    interview.outcome_notes = outcome_notes
    interview.updated_at = _utc_now_naive()

    if interview.application_id:
        app_result = await db.execute(select(Application).where(Application.id == interview.application_id))
        application = app_result.scalar_one_or_none()
        if application:
            if body.outcome == "selected":
                application.status = ApplicationStatus.selected
                outcome_title = "Congratulations:"
                outcome_msg = f"You have been selected after your interview for '{interview.title}'."
                if outcome_notes:
                    outcome_msg = f"{outcome_msg} {outcome_notes}"
                notif_type = NotificationType.shortlisted
                outcome_email_title = "Congratulations — You're Selected"
                notify = True
            elif body.outcome == "rejected":
                application.status = ApplicationStatus.rejected
                application.rejection_reason = outcome_notes or "Not selected after interview"
                outcome_title = "Interview Outcome Update:"
                outcome_msg = (
                    f"Thank you for interviewing. Unfortunately you were not selected for '{interview.title}'."
                )
                if outcome_notes:
                    outcome_msg = f"{outcome_msg} {outcome_notes}"
                notif_type = NotificationType.rejected
                outcome_email_title = "Interview Outcome Update"
                notify = True
            elif body.outcome == "no_show":
                # Back to shortlisted so Applied Jobs shows Shortlisted (not Interview),
                # and recruiter can schedule again.
                application.status = ApplicationStatus.shortlisted
                outcome_title = "Interview update:"
                outcome_msg = (
                    f"Your interview for '{interview.title}' was marked as not completed "
                    f"({outcome_notes}). The recruiter may contact you to reschedule."
                )
                notif_type = NotificationType.general
                outcome_email_title = "Interview not completed"
                notify = True
            else:
                application.status = ApplicationStatus.shortlisted
                outcome_title = "Interview cancelled:"
                outcome_msg = (
                    f"Your interview for '{interview.title}' was cancelled ({outcome_notes})."
                )
                notif_type = NotificationType.general
                outcome_email_title = "Interview cancelled"
                notify = True

            if notify:
                await create_notification(
                    db=db,
                    user_id=interview.seeker_id,
                    type=notif_type,
                    title=outcome_title,
                    message=outcome_msg,
                    related_job_id=str(interview.job_id),
                    related_user_id=str(provider.id),
                )
                seeker_email_res = await db.execute(
                    select(User.email, User.first_name).where(User.id == interview.seeker_id)
                )
                seeker_email_row = seeker_email_res.first()
                if seeker_email_row and seeker_email_row.email:
                    from app.shared.services.notification_service import queue_notification_email

                    queue_notification_email(
                        seeker_email_row.email,
                        outcome_email_title,
                        outcome_msg,
                        seeker_email_row.first_name or "there",
                    )

    await log_audit_event(
        db,
        provider,
        action="STATUS_CHANGE",
        entity_type="interview",
        entity_id=str(interview.id),
        entity_name=interview.title,
        description=f"Recorded interview outcome: {body.outcome}",
        changes={
            "outcome": body.outcome,
            "status": interview.status.value,
            "reason_code": body.reason_code,
        },
        source_portal="job_portal",
    )
    await db.commit()
    await db.refresh(interview)

    job_res = await db.execute(select(JobPosting.title).where(JobPosting.id == interview.job_id))
    job_title = job_res.scalar()
    seeker_res = await db.execute(
        select(User.first_name, User.last_name).where(User.id == interview.seeker_id)
    )
    seeker_data = seeker_res.first()
    s_fn, s_ln = seeker_data if seeker_data else ("Unknown", "User")

    return await _interview_out(
        interview,
        provider,
        job_title=job_title,
        seeker_name=f"{s_fn} {s_ln}",
    )
