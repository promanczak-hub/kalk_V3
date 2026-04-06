from core.database import supabase

v = (
    supabase.table("vehicle_synthesis")
    .select("id, brand, model, offer_number, configuration_code")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
    .data
)
for x in v:
    print(x)

k = (
    supabase.table("vehicle_synthesis")
    .select("id, brand, model, offer_number, configuration_code")
    .ilike("model", "%Kodiaq%")
    .execute()
    .data
)
for x in k:
    print("Found Kodiaq:", x)
