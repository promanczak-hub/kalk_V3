import sys
import logging
from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rebuild_all():
    logger.info("Truncating vehicle_matrix_cache table...")
    # There is no direct truncate via PostgREST. We can delete all where id > 0 or Kalkulacja > 0
    # Wait, PostgREST doesn't easily support DELETE ALL. It's better to just do it via HTTP if possible, or execute a raw query.
    # Actually, we can use the local psycopg2 or just Supabase raw sql. Let's try raw REST delete.
    try:
        supabase.table("vehicle_matrix_cache").delete().gt("duration_months", 0).execute()
    except Exception as e:
        logger.error(f"Failed to delete via REST, skipping or it might have worked: {e}")
    
    logger.info("Fetching all vehicle IDs from vehicle_synthesis...")
    res = supabase.table("vehicle_synthesis").select("id").execute()
    if not res.data:
        logger.warning("No vehicles found!")
        return

    vehicle_ids = [str(row["id"]) for row in res.data]
    logger.info(f"Found {len(vehicle_ids)} vehicles to refresh.")
    
    # Refresh cache for all. This will dispatch Celery tasks automatically because of the delay() call in refresh_matrix_cache_for_vehicles.
    refresh_matrix_cache_for_vehicles(vehicle_ids)
    logger.info(f"Dispatched {len(vehicle_ids)} tasks to Celery successfully.")

if __name__ == "__main__":
    rebuild_all()
