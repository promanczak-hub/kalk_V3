import os
import json
import logging
from typing import Any

from google.cloud import tasks_v2

from core.settings import APP_ENV

logger = logging.getLogger(__name__)

CLOUD_RUN_URL = os.environ.get(
    "CLOUD_RUN_URL", "https://you-cloud-run-domain.a.run.app"
)
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "express-handlorz")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "europe-central2")
CLOUD_TASKS_QUEUE = os.environ.get("CLOUD_TASKS_QUEUE", "kalk-tasks-queue")
SERVICE_ACCOUNT_EMAIL = os.environ.get("SERVICE_ACCOUNT_EMAIL", "")


class TaskDispatcher:
    @staticmethod
    def dispatch(task_func: Any, *args: Any, **kwargs: Any) -> None:
        """
        Uniwersalny dispatcher zadań.
        Jeśli APP_ENV == 'local', wywołuje zadanie za pomocą Celery.
        W przeciwnym wypadku, wrzuca zadanie do Google Cloud Tasks.
        """
        if APP_ENV == "local" or APP_ENV == "test":
            logger.info(f"Local Environment: Dispatching Celery task: {task_func.name}")
            task_func.apply_async(args=args, kwargs=kwargs)
        else:
            task_name = task_func.name
            logger.info(f"Production Environment: Enqueuing Cloud Task: {task_name}")
            TaskDispatcher._enqueue_cloud_task(task_name, args, kwargs)

    @staticmethod
    def _enqueue_cloud_task(task_name: str, args: tuple, kwargs: dict) -> None:
        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(GCP_PROJECT_ID, GCP_LOCATION, CLOUD_TASKS_QUEUE)

        # Map the task_name to our FastApi Webhook endpoint
        # Example: tasks.matrix_tasks.process_kalkulacja_matrix_task -> /_tasks/tasks.matrix_tasks.process_kalkulacja_matrix_task
        url = f"{CLOUD_RUN_URL}/_tasks/{task_name}"

        payload = {"args": args, "kwargs": kwargs}
        payload_bytes = json.dumps(payload).encode()

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "headers": {"Content-type": "application/json"},
                "body": payload_bytes,
            }
        }

        if SERVICE_ACCOUNT_EMAIL:
            task["http_request"]["oidc_token"] = {
                "service_account_email": SERVICE_ACCOUNT_EMAIL
            }

        try:
            response = client.create_task(request={"parent": parent, "task": task})
            logger.info(f"Created task {response.name}")
        except Exception as e:
            logger.error(f"Failed to create Cloud Task: {e}")
            raise
