import asyncio
from core.database import supabase

async def main():
    res = supabase.table('vehicle_synthesis').select('id, brand, model').ilike('brand', '%skoda%').ilike('model', '%octavia%').execute()
    vehicles = res.data
    for v in vehicles:
        print(f"Vehicle: {v['id']} {v['brand']} {v['model']}")
        
        cache_0 = supabase.table('vehicle_matrix_cache').select('*').eq('vehicle_id', v['id']).eq('margin_pct', 0).eq('duration_months', 48).eq('annual_mileage', 15000).execute()
        if cache_0.data:
            print(f"  Cache (0 margin, 48m, 15k): {cache_0.data[0]['monthly_price_net']}")
        else:
            print("  Cache not found for 0 margin, 48m, 15k")
            
        cache_14 = supabase.table('vehicle_matrix_cache').select('*').eq('vehicle_id', v['id']).eq('margin_pct', 14).eq('duration_months', 48).eq('annual_mileage', 15000).execute()
        if cache_14.data:
            print(f"  Cache (14% margin, 48m, 15k): {cache_14.data[0]['monthly_price_net']}")
        else:
            print("  Cache not found for 14% margin, 48m, 15k")

asyncio.run(main())
