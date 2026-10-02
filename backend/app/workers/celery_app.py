from celery import Celery

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

celery_app = Celery(
    "helpdesk",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "sla-escalation-check": {
            "task": "app.workers.tasks.sla_check",
            "schedule": 60.0,
        },
    },
)
