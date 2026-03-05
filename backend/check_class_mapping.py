from core.database import supabase

print("=== samar_classes ===")
r = supabase.table("samar_classes").select("id, name").order("id").execute()
for x in r.data:
    print(f"  {x['id']:3d} | {x['name']}")

print("\n=== KlasaSAMAR_czak ===")
r2 = supabase.table("KlasaSAMAR_czak").select("col_0, col_1").order("col_0").execute()
for x in r2.data:
    print(f"  {x['col_0']:3d} | {x['col_1']}")
