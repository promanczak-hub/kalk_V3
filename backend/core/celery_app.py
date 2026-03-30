import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

celery_app = Celery(
    "kalk_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.sample_tasks",
        "tasks.cache_tasks",
        "tasks.enrichment_tasks",
        "tasks.matrix_tasks",
        "tasks.matrix_watchdog",
        "core.celery_tasks",
        "core.pdf_pipeline.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "process_document_task": {"queue": "uploads"},
        "extract_pdf_pricelist_task": {"queue": "uploads"},
    },
    beat_schedule={
        "prewarm-global-filters-every-15-mins": {
            "task": "tasks.cache_tasks.prewarm_global_filters_cache",
            "schedule": 900.0,  # 15 minutes in seconds
        },
        "matrix-watchdog-every-5-mins": {
            "task": "matrix_watchdog_task",
            "schedule": 300.0,  # 5 minutes in seconds
        },
    },
)
