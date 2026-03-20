import logging

from core.celery_app import celery_app

from core.matrix_cache_job import process_single_kalkulacja_matrix_task

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_kalkulacja_matrix_task(self, kalkulacja_id: str, trace_id: str | None = None) -> str:
    """
    Celery task that computes and caches the matrix for a single historical calculation.
    """
    task_trace_id = trace_id or self.request.id or "UNKNOWN_CELERY_TRACE"
    logger.info("Executing Celery task for kalkulacja_id: %s [Trace: %s]", kalkulacja_id, task_trace_id)
    try:
        process_single_kalkulacja_matrix_task(kalkulacja_id, celery_task_id=self.request.id, trace_id=task_trace_id)
        return f"Cache refreshed for kalkulacja {kalkulacja_id}"
    except Exception as e:
        logger.error("Failed to process kalkulacja matrix in Celery task: %s [Trace: %s]", e, task_trace_id)
        raise
