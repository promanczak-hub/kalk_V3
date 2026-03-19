import logging
from typing import List, Optional

from core.celery_app import celery_app
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_matrix_refresh_task(
    self, vehicle_ids: List[str], job_id: Optional[str] = None
) -> str:
    """
    Celery task that refreshes matrix calculations for a given chunk of vehicles.
    """
    logger.info("Executing Celery batch matrix refresh for %s vehicles, job_id: %s", len(vehicle_ids), job_id)
    try:
        # Pasa the task ID as the job_id if not provided
        effective_job_id = job_id or self.request.id
        refresh_matrix_cache_for_vehicles(vehicle_ids, effective_job_id)
        return "Cache refreshed successfully"
    except Exception as e:
        logger.error(f"Failed to process matrix refresh in Celery task: {e}")
        raise
