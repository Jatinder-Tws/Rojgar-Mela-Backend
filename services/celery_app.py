"""
Celery application for the JobMatch backend.

Uses Redis as both broker and result backend.
Worker is started separately: celery -A services.celery_app worker --loglevel=info
"""
from celery import Celery
from config import settings

celery_app = Celery(
    "jobmatch",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["services.celery_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry on connection errors
    broker_connection_retry_on_startup=True,
)
