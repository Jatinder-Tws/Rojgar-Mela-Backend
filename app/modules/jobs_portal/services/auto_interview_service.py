import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs_portal.models.application import Application, ApplicationStatus
from app.modules.jobs_portal.models.interview import Interview, InterviewSource, InterviewStatus, InterviewType
from app.modules.jobs_portal.models.job import JobPosting
from app.shared.models.notification import NotificationType
from app.modules.jobs_portal.models.provider_interview_settings import ProviderInterviewSettings
from app.shared.models.user import User
from app.modules.jobs_portal.services.interview_flow import auto_schedule_block_reason
from app.modules.jobs_portal.services.interview_scheduling_service import find_next_available_slot
from app.shared.services.notification_service import create_notification

logger = logging.getLogger(__name__)


def _interview_type_for_email(value) -> str:
    if value is None:
        return "video"
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


async def auto_schedule_for_application(
    db: AsyncSession,
    application: Application,
    provider: User,
    job: JobPosting,
) -> Optional[Interview]:
    if not application.seeker_id:
        logger.info(
            "Skipping auto-schedule for application %s: no seeker_id",
            application.id,
        )
        return None

    existing = await db.execute(
        select(Interview.id).where(
            Interview.application_id == application.id,
            Interview.status.in_([InterviewStatus.scheduled, InterviewStatus.completed]),
        )
    )
    if existing.first():
        return None

    settings_result = await db.execute(
        select(ProviderInterviewSettings)
        .options(selectinload(ProviderInterviewSettings.availability_windows))
        .where(ProviderInterviewSettings.provider_id == provider.id)
    )
    settings = settings_result.scalar_one_or_none()
    if not settings or not settings.auto_schedule_enabled:
        return None
    block_reason = auto_schedule_block_reason(
        settings.default_interview_type,
        settings.default_meeting_link,
        settings.default_location,
        bool(settings.availability_windows),
    )
    if block_reason:
        await create_notification(
            db=db,
            user_id=str(provider.id),
            type=NotificationType.general,
            title="Auto-schedule Failed",
            message=f"Could not auto-schedule an interview for '{job.title}'. {block_reason}",
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
            title="Auto-schedule Failed",
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

    kind = (settings.default_interview_type or "video").strip().lower()
    interview_type = InterviewType.walk_in if kind == "walk_in" else InterviewType.video
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
            interview_type=interview_type,
            meeting_link=settings.default_meeting_link if interview_type == InterviewType.video else None,
            location=settings.default_location if interview_type == InterviewType.walk_in else None,
            scheduled_at=scheduled_at,
            scheduled_period=scheduled_period,
            source=InterviewSource.auto,
            status=InterviewStatus.scheduled,
        )
        try:
            async with db.begin_nested():
                db.add(interview)
                await db.flush()
            break
        except IntegrityError:
            logger.info("Auto-schedule slot conflict for provider %s at %s", provider.id, scheduled_at)
            current_slot = await find_next_available_slot(
                db, str(provider.id), after=scheduled_at
            )
    else:
        return None

    if interview is None:
        return None

    application.status = ApplicationStatus.interviewing

    await create_notification(
        db=db,
        user_id=str(application.seeker_id),
        type=NotificationType.match,
        title="Interview Scheduled",
        message=(
            f"{provider.first_name or 'The employer'} has scheduled an interview "
            f"for '{job.title}'. Check your dashboard for date and time."
        ),
        related_job_id=str(job.id),
        related_user_id=str(provider.id),
        auto_commit=True,
    )

    seeker_row = await db.execute(select(User).where(User.id == application.seeker_id))
    seeker = seeker_row.scalar_one_or_none()
    if seeker and seeker.email:
        try:
            from app.shared.services.celery_tasks import queue_interview_scheduled_email

            queue_interview_scheduled_email(
                to_email=seeker.email,
                seeker_name=seeker.first_name or "there",
                job_title=job.title,
                company_name=provider.company_name
                or f"{provider.first_name or ''} {provider.last_name or ''}".strip(),
                scheduled_at=interview.scheduled_at.isoformat()
                if hasattr(interview.scheduled_at, "isoformat")
                else str(interview.scheduled_at),
                interview_type=_interview_type_for_email(interview.interview_type),
                meeting_link=interview.meeting_link,
                location=interview.location,
                agenda=interview.agenda,
                scheduled_period=interview.scheduled_period,
                interviewer_name=interview.interviewer_name,
            )
        except Exception:
            logger.exception(
                "Failed to queue auto-interview email to %s for application %s",
                seeker.email,
                application.id,
            )

    return interview
