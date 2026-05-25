"""Celery application. Broker + result backend = Redis."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "Doc-Hub",
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=840,
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Routing — separate queue for dead letters
    task_routes={
        "app.workers.tasks.ingest_document": {"queue": "ingestion"},
        "app.workers.tasks.handle_dead_letter": {"queue": "dead_letter"},
    },
    result_expires=86400,
)
