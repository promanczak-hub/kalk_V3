import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

# get latest kalkulacja
print("Fetching latest kalkulacja_id from db...")
resp = sb.table('kalkulacje').select('id, vehicle_id').order('created_at', desc=True).limit(1).execute()
if not resp.data:
    print("No kalkulacje found.")
else:
    k_id = resp.data[0]['id']
    v_id = resp.data[0]['vehicle_id']
    print(f"Latest kalkulacja_id: {k_id} for vehicle {v_id}")
    
    # fetch matrix cache
    res2 = sb.table('vehicle_matrix_cache').select('duration_months, annual_mileage, kalkulacja_id').eq('kalkulacja_id', k_id).execute()
    data = res2.data
    print(f"Found {len(data)} rows in matrix cache for this kalkulacja.")
    
    # check for duplicates
    seen = set()
    dupes = 0
    for r in data:
        pair = (r['duration_months'], r['annual_mileage'])
        if pair in seen:
            dupes += 1
        seen.add(pair)
    print(f"Duplicates: {dupes}")
