import asyncio
import logging
from typing import Optional
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal, import_all_models

# Ensure all SQLAlchemy models are registered in the worker process
import_all_models()

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to safely run async functions inside synchronous Celery worker tasks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.create_task(coro)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── HIGH PRIORITY QUEUE TASKS ──────────────────────────────────────────────────

@celery_app.task(
    name="send_otp_email_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 2},
    retry_backoff=True,
)
def send_otp_email_task(email: str, otp: str, first_name: str = "there"):
    """Task for sending OTP emails via high_priority queue with automatic retries."""
    async def _send():
        from app.shared.services.email_service import send_otp_email
        await send_otp_email(to_email=email, otp=otp, first_name=first_name or "there")

    logger.info(f"[Task: send_otp_email_task] Enqueued OTP for {email}")
    run_async(_send())


@celery_app.task(
    name="send_password_reset_email_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 2},
    retry_backoff=True,
)
def send_password_reset_email_task(email: str, reset_token: str):
    """Task for sending password reset emails via high_priority queue with automatic retries."""
    async def _send():
        from app.shared.services.email_service import send_password_reset_email
        await send_password_reset_email(to_email=email, reset_token=reset_token)

    logger.info(f"[Task: send_password_reset_email_task] Enqueued reset for {email}")
    run_async(_send())


# ── DEAD LETTER QUEUE (DLQ) HANDLER ───────────────────────────────────────────

@celery_app.task(name="dead_letter_queue_task")
def dead_letter_queue_task(task_name: str, payload: dict, error_message: str, retries: int = 0):
    """Dead Letter Queue (DLQ) task capturing failed jobs after maximum retry exhaustion."""
    logger.error(
        f"[DLQ - DEAD LETTER QUEUE] Task '{task_name}' failed permanently after {retries} retries. "
        f"Error: {error_message}. Payload: {payload}"
    )


# ── EMAILS QUEUE TASKS ─────────────────────────────────────────────────────────

@celery_app.task(
    name="send_supervisor_welcome_email_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_supervisor_welcome_email_task(
    self,
    email: str,
    first_name: str,
    password: str,
    department: Optional[str] = None,
):
    """Task for sending supervisor welcome email with credentials via emails queue.
    Automatically moves to DLQ upon retry exhaustion.
    """
    async def _send():
        from app.shared.services.email_service import send_supervisor_welcome_email
        await send_supervisor_welcome_email(
            to_email=email,
            first_name=first_name,
            password=password,
            department=department,
        )

    try:
        logger.info(f"[Task: send_supervisor_welcome_email_task] Enqueued supervisor credentials email for {email}")
        run_async(_send())
    except Exception as exc:
        if self.request.retries >= (self.max_retries or 3):
            logger.error(f"[Task: send_supervisor_welcome_email_task] Max retries reached for {email}. Routing to DLQ.")
            dead_letter_queue_task.delay(
                task_name="send_supervisor_welcome_email_task",
                payload={"email": email, "first_name": first_name, "department": department},
                error_message=str(exc),
                retries=self.request.retries,
            )
        raise exc


@celery_app.task(
    name="send_welcome_email_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_welcome_email_task(email: str, name: str, role: str):
    """Task for sending welcome emails via emails queue."""
    async def _send():
        from app.shared.services.email_service import send_welcome_email
        await send_welcome_email(to_email=email, first_name=name or "there", role=role)

    logger.info(f"[Task: send_welcome_email_task] Enqueued welcome email for {email}")
    run_async(_send())


@celery_app.task(
    name="send_notification_email_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_notification_email_task(email: str, title: str, message: str, first_name: str = "there"):
    """Task for sending notification emails via emails queue."""
    async def _send():
        from app.shared.services.email_service import send_notification_email
        await send_notification_email(to_email=email, first_name=first_name, title=title, message=message)

    logger.info(f"[Task: send_notification_email_task] Enqueued notification for {email}")
    run_async(_send())


@celery_app.task(
    name="send_calendar_invite_email_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_calendar_invite_email_task(
    to_email: str,
    recipient_name: str,
    class_title: str,
    schedule_line: str,
    venue: str,
    ics_content: str,
    method: str = "REQUEST",
    role_label: str = "class",
):
    """Task for sending calendar invite emails via emails queue."""
    async def _send():
        from app.shared.services.email_service import send_class_calendar_invite_email
        await send_class_calendar_invite_email(
            to_email,
            recipient_name,
            class_title,
            schedule_line,
            venue,
            ics_content,
            method=method,
            role_label=role_label,
        )

    logger.info(f"[Task: send_calendar_invite_email_task] Enqueued invite for {to_email}")
    run_async(_send())


@celery_app.task(
    name="send_inquiry_reply_email",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_inquiry_reply_email(to_email: str, subject: str, body: str = "", message_body: str = ""):
    """Task for sending support inquiry reply emails via emails queue."""
    async def _send():
        from app.shared.services.email_service import _send_email, _notification_message_html

        content = body or message_body
        html = f"<p>{_notification_message_html(content)}</p>"
        await _send_email(to_email, subject, html)

    logger.info(f"[Task: send_inquiry_reply_email] Enqueued reply for {to_email}")
    run_async(_send())


# ── BROADCAST QUEUE TASKS ──────────────────────────────────────────────────────

@celery_app.task(
    name="broadcast_bulk_email_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    retry_backoff=True,
)
def broadcast_bulk_email_task(campaign_id: str, job_id: Optional[str] = None, is_resend: bool = False):
    """Task for processing bulk email campaigns via broadcast queue."""
    async def _run():
        from app.modules.super_admin.services.email_campaign_service import (
            run_campaign_send_job,
            run_campaign_resend_failed_job,
        )
        effective_job_id = job_id or campaign_id
        if is_resend:
            await run_campaign_resend_failed_job(effective_job_id, campaign_id)
        else:
            await run_campaign_send_job(effective_job_id, campaign_id)

    logger.info(f"[Task: broadcast_bulk_email_task] Executing campaign {campaign_id} (is_resend={is_resend})")
    run_async(_run())


# ── AI AND HEAVY QUEUE TASKS ────────────────────────────────────────────────────

@celery_app.task(
    name="process_bulk_candidate_import_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 15},
    retry_backoff=True,
)
def process_bulk_candidate_import_task(job_id: str, file_path: str, role: str = "seeker"):
    """Task for bulk candidate CSV import processing via ai_and_heavy queue."""
    async def _run():
        from app.modules.super_admin.services.super_admin_bulk_import import run_bulk_import_job
        await run_bulk_import_job(job_id=job_id, file_path=file_path, role=role)

    logger.info(f"[Task: process_bulk_candidate_import_task] Processing import job {job_id} for role {role}")
    run_async(_run())


@celery_app.task(
    name="generate_seeker_embeddings_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 15},
    retry_backoff=True,
)
def generate_seeker_embeddings_task(seeker_id: str):
    """Task for asynchronous seeker embedding generation via ai_and_heavy queue."""
    async def _run():
        async with AsyncSessionLocal() as db:
            from app.modules.jobs_portal.services.seeker_matching_service import generate_and_save_seeker_embedding
            await generate_and_save_seeker_embedding(db, seeker_id)

    logger.info(f"[Task: generate_seeker_embeddings_task] Generating embeddings for seeker {seeker_id}")
    run_async(_run())


@celery_app.task(
    name="run_external_matching_for_job",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    retry_backoff=True,
)
def run_external_matching_for_job(job_id: str):
    """Match a newly posted job against external (guest) candidates."""
    async def _run():
        from app.modules.jobs_portal.services.external_candidate_matching_service import (
            proactive_match_job_to_external_candidates,
        )
        await proactive_match_job_to_external_candidates(job_id)

    logger.info(f"[Task: run_external_matching_for_job] Matching externals for job {job_id}")
    run_async(_run())


@celery_app.task(
    name="improve_resume_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    retry_backoff=True,
)
def improve_resume_task(
    job_title: str,
    job_description: str,
    technologies,
    user_id: str,
):
    """Analyze a seeker's latest resume against a target job via Gemini."""
    async def _run():
        from sqlalchemy import select
        from app.modules.jobs_portal.models.resume import Resume
        from app.modules.jobs_portal.services.ai_improvement_suggestion_service import (
            analyze_resume_multi,
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Resume)
                .where(Resume.user_id == user_id)
                .order_by(Resume.created_at.desc())
                .limit(1)
            )
            resume = result.scalars().first()
            if not resume or not (resume.parsed_text or "").strip():
                raise ValueError("Resume text not found")
            return await analyze_resume_multi(
                {
                    "job_title": job_title,
                    "job_description": job_description,
                    "technologies": technologies,
                },
                resume.parsed_text,
            )

    logger.info(f"[Task: improve_resume_task] Improving resume for user {user_id}")
    return run_async(_run())


@celery_app.task(
    name="invalidate_seeker_matches_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    retry_backoff=True,
)
def invalidate_seeker_matches_task(seeker_id: str):
    """Task for invalidating and re-embedding seeker matches via ai_and_heavy queue."""
    async def _run():
        from app.modules.jobs_portal.services.seeker_matching_service import invalidate_seeker_matches
        await invalidate_seeker_matches(seeker_id)

    logger.info(f"[Task: invalidate_seeker_matches_task] Invalidation enqueued for seeker {seeker_id}")
    run_async(_run())


# ── DEFAULT QUEUE TASKS ────────────────────────────────────────────────────────

@celery_app.task(name="process_training_class_lifecycles")
def process_training_class_lifecycles():
    """Scheduled task for updating training class lifecycles via default queue."""
    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                from app.modules.training_portal.services.training_portal_class_lifecycle import process_all_class_lifecycles
                res = await process_all_class_lifecycles(db)
                await db.commit()
                logger.info(f"[Task: process_training_class_lifecycles] Lifecycle sweep result: {res}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Error in process_training_class_lifecycles task: {e}", exc_info=True)

    run_async(_run())


@celery_app.task(name="process_expired_token_bookings")
def process_expired_token_bookings():
    """Daily scheduled task: expire token-booked course seats whose 5-day venue-visit
    deadline has passed without SuperAdmin confirmation."""
    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                from app.modules.training_portal.services.training_portal_class_lifecycle import process_expired_token_visits
                res = await process_expired_token_visits(db)
                await db.commit()
                logger.info(f"[Task: process_expired_token_bookings] Sweep result: {res}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Error in process_expired_token_bookings task: {e}", exc_info=True)

    run_async(_run())


@celery_app.task(name="sync_scholarships_task")
def sync_scholarships_task():
    """Periodic 5-hour task to fetch open scholarships from Unstop and Buddy4Study,
    upsert them into database, and refresh Redis cache."""
    async def _run():
        try:
            from app.shared.services.scholarship_sync_service import ScholarshipSyncService
            result = await ScholarshipSyncService.sync_all_scholarships()
            logger.info(f"[Task: sync_scholarships_task] Sync completed: {result}")
            return result
        except Exception as e:
            logger.error(f"[Task: sync_scholarships_task] Error syncing scholarships: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    return run_async(_run())
