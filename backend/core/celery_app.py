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
        "process_document_task_from_storage": {"queue": "uploads"},
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
        # Safety net: catch vehicles whose phase_2 extraction skipped or
        # failed the embedding step (e.g. Celery hiccup, empty embedding
        # text, transient API error). Without this, missing vehicles stay
        # invisible to semantic search until someone notices.
        "backfill-vehicle-embeddings-every-6h": {
            "task": "tasks.enrichment_tasks.backfill_vehicle_embeddings",
            "schedule": 21600.0,  # 6 hours
        },
        # Fast-lane: zbieraj świeżo wyekstrahowane pojazdy (created_at <2h)
        # i te jawnie zarejestrowane w Redis SET embedding:pending. Mały N
        # → tani cykl. Skraca worst-case okno "świeży pojazd bez embeddings"
        # z 6h do <10 min, bez hammerowania Vertex AI pełnym katalogiem.
        "backfill-recent-vehicles-every-10-min": {
            "task": "tasks.enrichment_tasks.backfill_recent_vehicle_embeddings",
            "schedule": 600.0,  # 10 minutes
        },
    },
)
