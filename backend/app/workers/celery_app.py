from __future__ import annotations

from celery import Celery

from app.core.config import settings

broker = settings.REDIS_URL if not settings.CELERY_EAGER else "memory://"

celery_app = Celery(
    "datasentry",
    broker=broker,
    backend=broker if not settings.CELERY_EAGER else None,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_always_eager=settings.CELERY_EAGER,
    task_eager_propagates=settings.CELERY_EAGER,
    beat_schedule={
        "tick-monitors": {
            "task": "app.workers.tasks.run_due_monitors",
            "schedule": 60.0,
        },
    },
)

# Import tasks so they are registered.
from app.workers import tasks  # noqa: E402,F401
