from core.celery_app import celery_app
from api.scoring_search_routes import _redis_set, _PREFIX, _TTL_FILTERS, _params_hash
from core.database import supabase
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def prewarm_global_filters_cache() -> str:
    """Fetches the global (empty context) reverse search filters and saves to Redis."""
    logger.info("Starting global filters pre-warm task...")
    try:
        req_params = {
            "p_brands": None,
            "p_models": None,
            "p_samar_class_ids": None,
            "p_current_filters": {},
        }

        # Calculate exactly the same hash as the empty AvailableFiltersRequest would
        import json

        dumped_json = json.dumps(
            {"brands": [], "models": [], "samar_class_ids": [], "current_filters": {}}
        ).replace(" ", "")

        params_hash = _params_hash(dumped_json)
        cache_key = f"{_PREFIX}filters:{params_hash}"

        resp = supabase.rpc("rpc_get_available_filters", req_params).execute()
        result = resp.data or {}

        _redis_set(cache_key, result, _TTL_FILTERS)
        logger.info(
            f"Successfully pre-warmed global filters cache under key: {cache_key}"
        )
        return "Cache pre-warmed"
    except Exception as e:
        logger.error(f"Failed to prewarm filters cache: {e}")
        return f"Error: {e}"
