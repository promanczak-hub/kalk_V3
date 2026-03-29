from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, List, Dict
import logging

from core.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/_tasks", tags=["tasks"])


class TaskPayload(BaseModel):
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}


@router.post("/{task_name}")
async def execute_cloud_task(task_name: str, payload: TaskPayload, request: Request):
    """
    Punkt wejścia dla webhooków z Google Cloud Tasks.
    Na podstawie nazwy zadania odnajduje funkcję zrejestrowaną w Celery i wywołuje ją synchronicznie.
    """
    logger.info(f"Received Cloud Task Webhook for: {task_name}")

    # (Opcjonalnie) Możesz tutaj dodać walidację nagłówków autoryzacyjnych wygenerowanych przez Cloud Tasks (OIDC).
    # auth_header = request.headers.get("Authorization")

    task_func = celery_app.tasks.get(task_name)
    if not task_func:
        logger.error(f"Task {task_name} not found in Celery registry.")
        raise HTTPException(status_code=404, detail=f"Task {task_name} not found.")

    try:
        # Wywołujemy funkcję synchronicznie na serwerze Cloud Run
        logger.info(
            f"Executing task: {task_name} with args: {payload.args}, kwargs: {payload.kwargs}"
        )
        result = task_func(*payload.args, **payload.kwargs)
        logger.info(f"Task executed successfully. Result: {result}")
        return {"status": "ok", "result": str(result)}
    except Exception as e:
        logger.error(f"Error executing task {task_name}: {e}")
        # Ważne: Zwracamy kod błędu 500 by Cloud Tasks spróbował ponowić żądanie na podstawie retry_config
        raise HTTPException(status_code=500, detail=str(e))
