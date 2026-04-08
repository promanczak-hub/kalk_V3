from core.database import supabase

res_przebieg = (
    supabase.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB. PRZEBIEG")
    .execute()
)
rows = res_przebieg.data[0]["data_rows"]
print("TAB. PRZEBIEG klucze col_1:")
for r in rows:
    print(r.get("col_1"))

print("\nsamar_classes w bazie:")
res_classes = supabase.table("samar_classes").select("id, name").execute()
for r in res_classes.data:
    if r["id"] in [3, 10]:
        print(r)
