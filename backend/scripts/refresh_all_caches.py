import sys
import os
import logging

# Enable logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles


def main():
    # Fetch all vehicle IDs from vehicle_synthesis
    response = supabase.table("vehicle_synthesis").select("id").execute()
    vehicle_ids = [row["id"] for row in response.data]

    logger.info(f"Starting refresh for {len(vehicle_ids)} vehicles...")

    # Process in smaller batches of 5 to see progress more frequently
    batch_size = 5
    for i in range(0, len(vehicle_ids), batch_size):
        batch = vehicle_ids[i : i + batch_size]
        logger.info(
            f"Processing batch {i // batch_size + 1}/{(len(vehicle_ids) - 1) // batch_size + 1}..."
        )
        refresh_matrix_cache_for_vehicles(batch)
        logger.info(f"Batch {i // batch_size + 1} complete.")


if __name__ == "__main__":
    main()
