from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import delete, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from models.application import Application, ApplicationStatus
from models.interview import Interview, InterviewSource, InterviewStatus, InterviewType
from models.provider_availability_window import ProviderAvailabilityWindow
from models.provider_interview_settings import ProviderInterviewSettings
from models.user import User
from models.job import JobPosting
from models.notification import NotificationType
from services.notification_service import create_notification
from schemas.interviews import InterviewCreate, InterviewOut, InterviewOutcomeUpdate
from schemas.interview_scheduling import ProviderInterviewSettingsUpdate


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


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
        settings = ProviderInterviewSettings(provider_id=provider_id)
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
        settings.availability_windows = []

    return settings


async def upsert_settings(
    db: AsyncSession,
    provider_id: str,
    body: ProviderInterviewSettingsUpdate,
) -> ProviderInterviewSettings:
    settings = await get_or_create_settings(db, provider_id)
    data = body.model_dump(exclude_unset=True, exclude={"windows"})

    for key, value in data.items():
        setattr(settings, key, value)

    if body.windows is not None:
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
                    # period=window.period,
                    start_period=window.start_period,
                    end_period=window.end_period
                )
            )

    settings.updated_at = _utc_now_naive()
    await db.flush()
    return settings


async def toggle_auto_schedule_db(
    db: AsyncSession,
    provider_id: str,
    auto_schedule_enabled: bool,
) -> ProviderInterviewSettings:
    settings = await get_or_create_settings(db, provider_id)
    if auto_schedule_enabled and not settings.availability_windows:
        raise HTTPException(
            status_code=400,
            detail="Configure availability windows before enabling auto-schedule",
        )
    settings.auto_schedule_enabled = auto_schedule_enabled
    await db.flush()
    return settings


async def load_busy_intervals(
    db: AsyncSession,
    provider_id: str,
    start_utc: datetime,
    end_utc: datetime,
    slot_duration_minutes: int,
) -> List[Tuple[datetime, datetime]]:
    result = await db.execute(
        select(Interview.scheduled_at).where(
            Interview.provider_id == provider_id,
            Interview.scheduled_at >= start_utc,
            Interview.scheduled_at < end_utc,
        )
    )
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
    # Validation: Prevent past scheduling
    if body.scheduled_at < datetime.now(timezone.utc):
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

    # Import locally to avoid circular import issues
    from services.interview_scheduling_service import assert_slot_available

    settings = await get_or_create_settings(db, provider.id)
    scheduled_at = body.scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)
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

    if body.application_id:
        app_result = await db.execute(select(Application).where(Application.id == body.application_id))
        application = app_result.scalar_one_or_none()
        if application:
            application.status = ApplicationStatus.interviewing
    
    # Notify seeker
    await create_notification(
        db=db,
        user_id=body.seeker_id,
        type=NotificationType.match,
        title=f"📅 Interview Scheduled: {body.title}",
        message=f"{provider.first_name} has scheduled an interview for '{job.title}'. Open your dashboard to see the date and time in your timezone.",
        related_job_id=body.job_id,
        related_user_id=str(provider.id)
    )

    await db.commit()
    await db.refresh(interview)
    
    # Enrichment for response
    seeker_result = await db.execute(select(User.first_name, User.last_name).where(User.id == body.seeker_id))
    seeker_data = seeker_result.first()
    s_fn, s_ln = (seeker_data.first_name, seeker_data.last_name) if seeker_data else ("Unknown", "User")
    
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
        item.provider_name = f"{i.provider.first_name} {i.provider.last_name}" if i.provider else "Unknown Provider"
        out.append(item)
        
    return out


async def record_interview_outcome(
    db: AsyncSession,
    interview_id: str,
    body: InterviewOutcomeUpdate,
    provider: User,
) -> InterviewOut:
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if interview.provider_id != provider.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if interview.status == InterviewStatus.completed:
        raise HTTPException(status_code=409, detail="Interview outcome already recorded")

    interview.status = InterviewStatus.completed
    if body.notes:
        interview.agenda = (interview.agenda or "") + f"\n\nOutcome notes: {body.notes}"

    if interview.application_id:
        app_result = await db.execute(select(Application).where(Application.id == interview.application_id))
        application = app_result.scalar_one_or_none()
        if application:
            if body.outcome == "selected":
                application.status = ApplicationStatus.selected
                outcome_title = "Congratulations! You were selected"
                outcome_msg = f"You have been selected after your interview for '{interview.title}'."
                notif_type = NotificationType.shortlisted
            else:
                application.status = ApplicationStatus.rejected
                application.rejection_reason = body.notes or "Not selected after interview"
                outcome_title = "Interview outcome update"
                outcome_msg = f"Thank you for interviewing. Unfortunately you were not selected for this role."
                notif_type = NotificationType.rejected

            await create_notification(
                db=db,
                user_id=interview.seeker_id,
                type=notif_type,
                title=outcome_title,
                message=outcome_msg,
                related_job_id=str(interview.job_id),
                related_user_id=str(provider.id),
            )

    await db.commit()
    await db.refresh(interview)

    job_res = await db.execute(select(JobPosting.title).where(JobPosting.id == interview.job_id))
    job_title = job_res.scalar()
    seeker_res = await db.execute(select(User.first_name, User.last_name).where(User.id == interview.seeker_id))
    seeker_data = seeker_res.first()
    s_fn, s_ln = seeker_data if seeker_data else ("Unknown", "User")

    item = InterviewOut.model_validate(interview)
    item.job_title = job_title
    item.seeker_name = f"{s_fn} {s_ln}"
    item.provider_name = f"{provider.first_name} {provider.last_name}"
    return item
