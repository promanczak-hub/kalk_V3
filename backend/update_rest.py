from supabase import create_client, Client

url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
key = "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"

supabase: Client = create_client(url, key)

print("Updating year 0 (Base WR)...")
res1 = (
    supabase.table("samar_class_depreciation_rates")
    .update({"base_depreciation_percent": 0.40})
    .eq("samar_class_id", 4)
    .eq("fuel_type_id", 2)
    .eq("year", 0)
    .execute()
)
print("Res1:", len(res1.data) if hasattr(res1, "data") else res1)

print("Updating year 4 (Options WR)...")
res2 = (
    supabase.table("samar_class_depreciation_rates")
    .update({"options_depreciation_percent": 0.26})
    .eq("samar_class_id", 4)
    .eq("fuel_type_id", 2)
    .eq("year", 4)
    .execute()
)
print("Res2:", len(res2.data) if hasattr(res2, "data") else res2)

# Check
check = (
    supabase.table("samar_class_depreciation_rates")
    .select("*")
    .eq("samar_class_id", 4)
    .eq("fuel_type_id", 2)
    .in_("year", [0, 4])
    .execute()
)
for c in check.data:
    print(
        f"year {c['year']}: base={c.get('base_depreciation_percent')}, opt={c.get('options_depreciation_percent')}"
    )
