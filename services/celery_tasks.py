"""
Celery tasks for embedding and matching jobs against seekers and external candidates.

These replace the FastAPI BackgroundTasks for job-creation matching,
giving us persistence, retries, and monitoring.

Worker command:
    celery -A services.celery_app worker --loglevel=info --pool=solo
"""
import asyncio
import logging

from services.celery_app import celery_app

logger = logging.getLogger(__name__)


# ── Helper: run an async function from a sync Celery task ────────────────
def _run_async(coro):
    """Bridge sync Celery task → async code.

    ``asyncio.run()`` creates a fresh event loop per call and closes it
    afterward. The process-global async SQLAlchemy engine (asyncpg) may still
    hold pooled connections bound to the *previous* loop; reusing them on the
    next task raises ``RuntimeError: ... attached to a different loop``.
    Dispose the engine after each run so the next task opens clean connections.
    """
    async def _wrapped():
        try:
            return await coro
        finally:
            from database import engine
            await engine.dispose()

    return asyncio.run(_wrapped())


# ── Individual matching tasks (can be called independently) ─────────────

@celery_app.task(name="run_seeker_matching_for_job", max_retries=3, default_retry_delay=30)
def run_seeker_matching_for_job(job_id: str):
    """Run pgvector + GPT re-rank for registered seekers against a job."""
    from services.seeker_matching_service import proactive_match_job_to_candidates

    async def _match():
        await proactive_match_job_to_candidates(job_id)

    try:
        _run_async(_match())
        logger.info(f"[CELERY] Seeker matching complete for job {job_id}")
    except Exception as exc:
        logger.exception(f"[CELERY] Seeker matching failed for job {job_id}: {exc}")
        raise celery_app.retry(exc=exc)


@celery_app.task(name="run_external_matching_for_job", max_retries=3, default_retry_delay=30)
def run_external_matching_for_job(job_id: str):
    """Run pgvector + GPT re-rank for external candidates against a job."""
    from services.external_candidate_matching_service import (
        proactive_match_job_to_external_candidates,
    )

    async def _match():
        await proactive_match_job_to_external_candidates(job_id)

    try:
        _run_async(_match())
        logger.info(f"[CELERY] External matching complete for job {job_id}")
    except Exception as exc:
        logger.exception(f"[CELERY] External matching failed for job {job_id}: {exc}")
        raise celery_app.retry(exc=exc)

    # ── After external matching completes, notify the job's provider via WebSocket ──
    _notify_provider_after_matching(job_id)


# ── Orchestration task (called from POST /api/jobs) ─────────────────────

@celery_app.task(name="embed_and_match_job", max_retries=3, default_retry_delay=60)
def embed_and_match_job_task(job_id: str):
    """
    Full job-creation pipeline:
      1. Embed job description → store pgvector
      2. Match registered seekers (similarity + GPT)
      3. Match external candidates (similarity + GPT)
    """
    from database import AsyncSessionLocal
    from services.seeker_matching_service import embed_and_store_job

    async def _pipeline():
        async with AsyncSessionLocal() as s:
            from models.job import JobPosting

            job_obj = await s.get(JobPosting, job_id)
            if not job_obj:
                logger.error(f"[CELERY] Job {job_id} not found — aborting pipeline")
                return

            # Step 1: Embed
            await embed_and_store_job(job_obj, s)
            logger.info(f"[CELERY] Embedding complete for job {job_id}")

    try:
        _run_async(_pipeline())
    except Exception as exc:
        logger.exception(f"[CELERY] Embedding failed for job {job_id}: {exc}")
        raise celery_app.retry(exc=exc)

    # Step 2 & 3: Run matching (each with its own retry)
    run_seeker_matching_for_job.delay(job_id)
    run_external_matching_for_job.delay(job_id)


# ── WebSocket notification helper ────────────────────────────────────────

def _notify_provider_after_matching(job_id: str):
    """
    Push a real-time update to the provider's dashboard.
    Runs inside a separate asyncio loop since we're in a sync Celery context.
    """
    from database import AsyncSessionLocal
    from sqlalchemy import select, func

    async def _push():
        async with AsyncSessionLocal() as db:
            from models.job import JobPosting
            from models.external_candidate_match import ExternalCandidateMatch

            # Get the job's provider_id
            row = await db.execute(
                select(JobPosting.provider_id, JobPosting.title).where(JobPosting.id == job_id)
            )
            job_info = row.fetchone()
            if not job_info:
                return
            provider_id, job_title = str(job_info[0]), job_info[1]

            # Count new external matches for this job
            count_row = await db.execute(
                select(func.count(ExternalCandidateMatch.id)).where(ExternalCandidateMatch.job_id == job_id)
            )
            count = count_row.scalar() or 0

            # Push WebSocket
            from services.websocket_manager import manager

            await manager.send_personal_message(
                {
                    "type": "EXTERNAL_MATCH_UPDATE",
                    "job_id": job_id,
                    "job_title": job_title,
                    "count": count,
                    "message": f"{count} external candidate(s) matched with '{job_title}'",
                },
                provider_id,
            )
            logger.info(
                f"[CELERY] WebSocket EXTERNAL_MATCH_UPDATE sent to provider {provider_id}: "
                f"{count} matches for job {job_id}"
            )

    try:
        asyncio.run(_push())
    except Exception as exc:
        logger.warning(f"[CELERY] WebSocket notification failed (non-critical): {exc}")


@celery_app.task(name="send_inquiry_reply_email", max_retries=3, default_retry_delay=30)
def send_inquiry_reply_email(to_email: str, subject: str, message_body: str):
    """Send support inquiry reply email using SMTP service in background."""
    from services.email_service import _send_email

    async def _send():
        html_content = f"""
        <html>
        <body style="font-family: sans-serif; line-height: 1.5; color: #333; margin: 0; padding: 20px; background-color: #f8fafc;">
            <div style="max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <h2 style="color: #4f46e5; border-bottom: 2px solid #e2e8f0; padding-bottom: 13px; margin-top: 0;">Support Inquiry Response</h2>
                <div style="font-size: 13px; color: #1e293b; white-space: pre-wrap; line-height: 1.6; margin-top: 20px; margin-bottom: 20px;">
{message_body}
                </div>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-top: 30px; margin-bottom: 20px;">
                <p style="font-size: 12px; color: #64748b; margin-bottom: 0;">This email is a response to the contact inquiry you submitted to the Mega Job Fair Organizing Committee on Rojgar Mela. Please do not reply to this automated email.</p>
            </div>
        </body>
        </html>
        """
        await _send_email(to_email, subject, html_content, raise_on_error=True)

    try:
        _run_async(_send())
        logger.info(f"[CELERY] Reply email sent successfully to {to_email}")
    except Exception as exc:
        logger.exception(f"[CELERY] Reply email delivery failed to {to_email}: {exc}")
        raise celery_app.retry(exc=exc)


@celery_app.task(name="improve_resume_task", max_retries=3, default_retry_delay=30)
def improve_resume_task(job_title: str, job_description: str, technologies: str, user_id: str):
    """Run resume improvement suggestion asynchronously."""
    from database import AsyncSessionLocal
    from sqlalchemy import select
    from models.resume import Resume
    from services.ai_improvement_suggestion_service import analyze_resume_multi

    async def _improve():
        async with AsyncSessionLocal() as s:
            tech_list = [t.strip() for t in technologies.split(",")]
            result = await s.execute(
                select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc()).limit(1)
            )
            resume = result.scalars().first()
            if not resume:
                raise ValueError("Resume not found")

            resume_text = (resume.parsed_text or '').strip()
            if not resume_text:
                import json
                resume_text = json.dumps(resume.parsed_json or {}, ensure_ascii=False)

            ai_result = await analyze_resume_multi(
                data={"job_title": job_title, "job_description": job_description, "technologies": tech_list},
                resume_text=resume_text,
            )
            return ai_result

    try:
        return _run_async(_improve())
    except Exception as exc:
        logger.exception(f"[CELERY] Resume improvement failed for user {user_id}: {exc}")
        raise celery_app.retry(exc=exc)


@celery_app.task(name="process_training_class_lifecycles")
def process_training_class_lifecycles():
    """Periodic: 15-min end reminders + auto-end live classes at scheduled end_time."""
    from database import AsyncSessionLocal
    from services.training_portal_class_lifecycle import process_all_class_lifecycles

    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                stats = await process_all_class_lifecycles(db)
                await db.commit()
                return stats
            except Exception:
                await db.rollback()
                raise

    try:
        stats = _run_async(_run())
        if stats and (stats.get("auto_ended") or stats.get("end_reminders") or stats.get("start_reminders")):
            logger.info("[CELERY] Class lifecycle sweep: %s", stats)
        return stats
    except Exception as exc:
        logger.exception("[CELERY] Class lifecycle sweep failed: %s", exc)
        raise


