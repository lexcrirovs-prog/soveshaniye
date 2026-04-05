from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "call_analytics",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 min
    task_soft_time_limit=1500,  # 25 min
    result_expires=3600,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "weekly-export": {
            "task": "app.tasks.export_task.export_calls",
            "schedule": crontab(hour=2, minute=0, day_of_week=1),  # Monday 02:00
            "args": ("7d",),
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
