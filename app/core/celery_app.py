from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange
from app.core.config import settings

celery_app = Celery(
    "jobmatch",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.shared.services.celery_tasks"],
)

default_exchange = Exchange("default", type="direct")
high_priority_exchange = Exchange("high_priority", type="direct")
emails_exchange = Exchange("emails", type="direct")
broadcast_exchange = Exchange("broadcast", type="direct")
ai_and_heavy_exchange = Exchange("ai_and_heavy", type="direct")
dead_letter_exchange = Exchange("dead_letter", type="direct")

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    task_default_queue="default",
    task_queues=(
        Queue("default", default_exchange, routing_key="default"),
        Queue("high_priority", high_priority_exchange, routing_key="high_priority"),
        Queue("emails", emails_exchange, routing_key="emails"),
        Queue("broadcast", broadcast_exchange, routing_key="broadcast"),
        Queue("ai_and_heavy", ai_and_heavy_exchange, routing_key="ai_and_heavy"),
        Queue("dead_letter", dead_letter_exchange, routing_key="dead_letter"),
    ),
    task_routes={
        "send_otp_email_task": {"queue": "high_priority"},
        "send_password_reset_email_task": {"queue": "high_priority"},
        "send_welcome_email_task": {"queue": "emails"},
        "send_supervisor_welcome_email_task": {"queue": "emails"},
        "dead_letter_queue_task": {"queue": "dead_letter"},
        "send_notification_email_task": {"queue": "emails"},
        "send_calendar_invite_email_task": {"queue": "emails"},
        "broadcast_bulk_email_task": {"queue": "broadcast"},
        "process_bulk_candidate_import_task": {"queue": "ai_and_heavy"},
        "generate_seeker_embeddings_task": {"queue": "ai_and_heavy"},
        "invalidate_seeker_matches_task": {"queue": "ai_and_heavy"},
        "run_external_matching_for_job": {"queue": "ai_and_heavy"},
        "improve_resume_task": {"queue": "ai_and_heavy"},
        "process_training_class_lifecycles": {"queue": "default"},
        "process_expired_token_bookings": {"queue": "default"},
        "sync_scholarships_task": {"queue": "default"},
    },
    beat_schedule={
        "process-training-class-lifecycles": {
            "task": "process_training_class_lifecycles",
            "schedule": 60.0,
            "options": {"queue": "default"},
        },
        "process-expired-token-bookings": {
            "task": "process_expired_token_bookings",
            "schedule": crontab(hour=1, minute=0),
            "options": {"queue": "default"},
        },
        "sync-scholarships-every-5-hours": {
            "task": "sync_scholarships_task",
            "schedule": crontab(minute=0, hour="*/5"),
            "options": {"queue": "default"},
        },
    },
)
