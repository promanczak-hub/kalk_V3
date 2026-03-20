import os
from celery import Celery
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "kalk_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.sample_tasks",
        "tasks.cache_tasks",
        "tasks.enrichment_tasks",
        "tasks.matrix_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    task_routes={
        "process_document_task": {"queue": "uploads"},
    },
    beat_schedule={
        "prewarm-global-filters-every-15-mins": {
            "task": "tasks.cache_tasks.prewarm_global_filters_cache",
            "schedule": 900.0,  # 15 minutes in seconds
        },
    },
)

