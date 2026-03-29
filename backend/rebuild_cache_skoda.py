import asyncio
from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

async def main():
    print("Fetching Skodas...")
    res = supabase.table('vehicle_synthesis').select('id, brand, model').eq('brand', 'SKODA').limit(20).execute()
    skodas = res.data or []
    print(f"Znaleziono {len(skodas)} pojazdów marki Skoda.")
    
    if not skodas:
        return

    v_ids = [s['id'] for s in skodas]
    print(f"Triggering cache refresh for {len(v_ids)} vehicles...")
    refresh_matrix_cache_for_vehicles(v_ids)
    print("Refresh tasks dispatched! Check Celery logs.")

asyncio.run(main())
