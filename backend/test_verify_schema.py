from supabase import create_client

url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
key = "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"
vehicle_id = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"

sb = create_client(url, key)
try:
    res = sb.schema("reverse_search").table("vehicle_feature_state").select("feature_key, value_numeric").eq("vehicle_id", vehicle_id).execute()
    print(f"Features for vehicle {vehicle_id}:")
    for r in res.data:
        val = r.get("value_numeric")
        if val is not None:
            print(f"  {r['feature_key']}: {val}")
except Exception as e:
    print(f"Error: {e}")
