import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application
from models.interview import Interview, InterviewSource
from models.job import JobPosting
from models.notification import NotificationType
from models.provider_interview_settings import ProviderInterviewSettings
from models.user import User
from services.interview_scheduling_service import find_next_available_slot
from services.notification_service import create_notification

logger = logging.getLogger(__name__)


async def auto_schedule_for_application(
    db: AsyncSession,
    application: Application,
    provider: User,
    job: JobPosting,
) -> Optional[Interview]:
    print("Auto-scheduling interview for application %s", application)
    print("Provider is %s", provider)
    print("Job is %s", job)
    print("the seeker is is ",application.seeker_id)
    print("the application id is ", application.id)
    if not application.seeker_id:
        logger.info(
            "Skipping auto-schedule for application %s: no seeker_id",
            application.id,
        )
        return None

    existing = await db.execute(
        select(Interview).where(
            Interview.application_id == application.id
            # Interview.source == InterviewSource.auto.value,
        )
    )
    existing_interview = existing.scalar_one_or_none()
    print("The existing result is ===================", existing_interview)
    if existing_interview:
        return None

    settings_result = await db.execute(
        select(ProviderInterviewSettings).where(
            ProviderInterviewSettings.provider_id == provider.id
        )
    )
    print("The setting result is ", settings_result)
    settings = settings_result.scalar_one_or_none()
    print("settings is available",settings)
    if not settings or not settings.auto_schedule_enabled:
        return None
    print("auto schedule is enabled")
    if not settings.availability_windows:
        await create_notification(
            db=db,
            user_id=str(provider.id),
            type=NotificationType.general,
            title="Auto-schedule: no availability configured",
            message=(
                f"Could not auto-schedule an interview for '{job.title}'. "
                "Add availability windows in interview settings."
            ),
            related_job_id=str(job.id),
            related_user_id=str(application.seeker_id),
            email_notification=False,
        )
        return None

    slot = await find_next_available_slot(db, str(provider.id))
    if not slot:
        await create_notification(
            db=db,
            user_id=str(provider.id),
            type=NotificationType.general,
            title="Auto-schedule: no free slots",
            message=(
                f"No interview slot available within the next {settings.lookahead_days} days "
                f"for '{job.title}'. Extend availability or schedule manually."
            ),
            related_job_id=str(job.id),
            related_user_id=str(application.seeker_id),
            email_notification=False,
        )
        return None

    interviewer_name = (
        settings.default_interviewer_name
        or f"{provider.first_name or ''} {provider.last_name or ''}".strip()
        or "HR Team"
    )
    title = settings.default_title or f"Interview - {job.title}"

    interview: Optional[Interview] = None
    current_slot = slot
    for _ in range(3):
        if not current_slot:
            return None
        scheduled_at, scheduled_period = current_slot
        interview = Interview(
            seeker_id=str(application.seeker_id),
            provider_id=str(provider.id),
            job_id=str(job.id),
            application_id=str(application.id),
            title=title,
            interviewer_name=interviewer_name,
            agenda=settings.default_agenda,
            scheduled_at=scheduled_at,
            scheduled_period=scheduled_period,
            source=InterviewSource.auto,
        )
        try:
            async with db.begin_nested():
                db.add(interview)
                await db.flush()
            break
        except IntegrityError:
            logger.info("Auto-schedule slot conflict for provider %s at %s", provider.id, scheduled_at)
            # rollback of the nested transaction was automatic; try next available slot
            current_slot = await find_next_available_slot(
                db, str(provider.id), after=scheduled_at
            )
    else:
        return None

    if interview is None:
        return None

    await create_notification(
        db=db,
        user_id=str(application.seeker_id),
        type=NotificationType.match,
        title=f"Interview Scheduled: {title}",
        message=(
            f"{provider.first_name or 'The employer'} has scheduled an interview "
            f"for '{job.title}'. Check your dashboard for date and time."
        ),
        related_job_id=str(job.id),
        related_user_id=str(provider.id),
    )

    return interview
