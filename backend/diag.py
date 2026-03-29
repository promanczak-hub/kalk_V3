import asyncio
import json
from core.database import supabase

async def main():
    res = supabase.table('vehicle_synthesis').select('id, brand, model').eq('brand', 'SKODA').limit(5).execute()
    
    if res.data:
        vid = res.data[0]['id']
        cache_res = supabase.table('vehicle_matrix_cache').select('monthly_price_net, duration_months, annual_mileage').eq('vehicle_id', vid).limit(5).execute()
        with open('cache_out.json', 'w') as f:
            json.dump(cache_res.data, f)

    rpc_res = supabase.rpc("rpc_reverse_search", {
        "p_brands": ["SKODA"],
        "p_models": [],
        "p_samar_class_ids": [],
        "p_trims": [],
        "p_vehicle_ids": [],
        "p_requirements": []
    }).execute()
    
    if rpc_res.data:
        with open('rpc_out.json', 'w') as f:
            json.dump(rpc_res.data[:2], f, indent=2)

asyncio.run(main())
