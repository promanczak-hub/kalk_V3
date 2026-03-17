"""
Skrypt regenerujący CAŁY cache matrixa dla wszystkich pojazdów.
Najpierw czyści starą tabelę, potem przelicza od nowa z pełnym zakresem przebiegów.
"""
import logging
from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CHUNK_SIZE = 5  # Ile aut na raz

if __name__ == "__main__":
    # 1. Pobierz wszystkie pojazdy
    res = supabase.table("vehicle_synthesis").select("id").execute()
    all_ids = [r["id"] for r in (res.data or [])]
    logger.info(f"Found {len(all_ids)} vehicles to process")
    
    # 2. Wyczyść stary cache
    logger.info("Clearing old cache...")
    supabase.table("vehicle_matrix_cache").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    logger.info("Old cache cleared")
    
    # 3. Przelicz w paczkach
    total = len(all_ids)
    done = 0
    for i in range(0, total, CHUNK_SIZE):
        chunk = all_ids[i:i+CHUNK_SIZE]
        logger.info(f"Processing chunk {i//CHUNK_SIZE + 1}/{(total + CHUNK_SIZE -1)//CHUNK_SIZE} ({len(chunk)} vehicles)")
        refresh_matrix_cache_for_vehicles(chunk)
        done += len(chunk)
        logger.info(f"Progress: {done}/{total} vehicles done")
    
    # 4. Podsumowanie
    res_cache = supabase.table("vehicle_matrix_cache").select("vehicle_id", count="exact").execute()
    logger.info(f"DONE! Cache now has {res_cache.count} rows")
