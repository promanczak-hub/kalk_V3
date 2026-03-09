from core.database import supabase

r = supabase.table("samar_classes").select("id, name").order("id").execute()
for x in r.data:
    print(f"{x['id']}: {x['name']}")
