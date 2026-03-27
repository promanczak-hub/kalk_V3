"""Matrix Watchdog — periodic Celery Beat task.

Runs every 5 minutes. Finds vehicles with ``verification_status = 'completed'``
that have zero rows in ``vehicle_matrix_cache`` and triggers
``refresh_matrix_cache_for_vehicles`` to fill the gap.

This acts as a self-healing mechanism: if the original Celery task was
lost (worker down, OOM, restart, etc.) the watchdog will automatically
re-generate the missing matrix within a few minutes.
"""

import logging
from typing import Any

from core.celery_app import celery_app
from core.database import supabase

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10  # Max vehicles to process per watchdog run


@celery_app.task(name="matrix_watchdog_task")
def matrix_watchdog_task() -> str:
    """Scan for completed vehicles without matrix cache and regenerate.
    (DISABLED per user request - user wants manual setup first)
    """
    logger.debug("[WATCHDOG] Watchdog is currently DISABLED.")
    return "OK — watchdog disabled"


def _find_vehicles_without_matrix() -> list[dict[str, Any]]:
    """Return completed vehicles that have no entries in vehicle_matrix_cache."""
    result = supabase.rpc(
        "find_vehicles_without_matrix",
        {"p_limit": _BATCH_SIZE},
    ).execute()

    if result.data:
        return result.data

    # Fallback: raw SQL via two queries if RPC doesn't exist yet
    logger.debug("[WATCHDOG] RPC not available, using fallback query.")
    return _find_vehicles_without_matrix_fallback()


def _find_vehicles_without_matrix_fallback() -> list[dict[str, Any]]:
    """Fallback: fetch completed vehicles and filter those without cache."""
    vs_res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model")
        .eq("verification_status", "completed")
        .execute()
    )
    all_vehicles = vs_res.data or []
    if not all_vehicles:
        return []

    vehicle_ids = [v["id"] for v in all_vehicles]

    # Fetch which ones already have cache
    cache_res = (
        supabase.table("vehicle_matrix_cache")
        .select("vehicle_id")
        .in_("vehicle_id", vehicle_ids)
        .execute()
    )
    cached_ids = {row["vehicle_id"] for row in (cache_res.data or [])}

    missing = [v for v in all_vehicles if v["id"] not in cached_ids]
    return missing[:_BATCH_SIZE]
