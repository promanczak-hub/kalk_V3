import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# We point to local redis by default or via env. If running in docker, REDIS_URL should be set.
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "kalk_worker",
    broker=redis_url,
    backend=redis_url,
    include=["core.celery_tasks", "tasks.matrix_tasks"],  # we will put tasks here
)

# Optional configuration, e.g. timeouts
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Ignore other content
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    task_routes={
        "process_document_task": {"queue": "uploads"},
    },
    # Worker configuration
    worker_prefetch_multiplier=1,  # One task per worker child process at a time (since they are heavy AI tasks)
)

if __name__ == "__main__":
    celery_app.start()
