import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "kalk_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.sample_tasks", "tasks.cache_tasks", "tasks.enrichment_tasks", "tasks.matrix_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    beat_schedule={
        "prewarm-global-filters-every-15-mins": {
            "task": "tasks.cache_tasks.prewarm_global_filters_cache",
            "schedule": 900.0,  # 15 minutes in seconds
        },
        "nightly-matrix-cache-refresh": {
            "task": "tasks.matrix_tasks.process_matrix_refresh_task",
            "schedule": crontab(hour=2, minute=0),
            "args": (None,),  # None triggers trigger_all_vehicles_cache_refresh
        },
    }
)
