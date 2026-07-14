"""Celery application + Beat schedule.

Scheduled jobs:
- hourly:      fetch Google Ads performance metrics
- every 6h:    run the autonomous AI optimization loop
- daily @06:00 UTC: generate daily performance reports
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "ai_ads_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=780,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "fetch-metrics-hourly": {
        "task": "app.worker.tasks.fetch_all_metrics",
        "schedule": crontab(minute=0),
    },
    "run-optimizations-every-6h": {
        "task": "app.worker.tasks.run_all_optimizations",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "daily-reports": {
        "task": "app.worker.tasks.generate_all_reports",
        "schedule": crontab(minute=0, hour=6),
    },
}
