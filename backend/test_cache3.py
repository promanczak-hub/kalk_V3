import asyncio
from core.database import supabase

async def main():
    vehicles = [
        '158e4de0-e3c9-488f-b224-676be5659a5d',
        'a6d6ff54-1dbb-4bb4-905e-71fcc240083a'
    ]
    for vid in vehicles:
        print(f"\nVehicle: {vid}")
        res = supabase.table('vehicle_matrix_cache').select('margin_pct, duration_months, annual_mileage, monthly_price_net').eq('vehicle_id', vid).eq('duration_months', 48).eq('annual_mileage', 15000).execute()
        for row in res.data:
            print(f"  {row}")

asyncio.run(main())
