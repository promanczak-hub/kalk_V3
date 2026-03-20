import logging

from core.celery_app import celery_app

from core.matrix_cache_job import process_single_kalkulacja_matrix_task

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_kalkulacja_matrix_task(self, kalkulacja_id: str) -> str:
    """
    Celery task that computes and caches the matrix for a single historical calculation.
    """
    logger.info("Executing Celery task for kalkulacja_id: %s", kalkulacja_id)
    try:
        process_single_kalkulacja_matrix_task(kalkulacja_id)
        return f"Cache refreshed for kalkulacja {kalkulacja_id}"
    except Exception as e:
        logger.error(f"Failed to process kalkulacja matrix in Celery task: {e}")
        raise
