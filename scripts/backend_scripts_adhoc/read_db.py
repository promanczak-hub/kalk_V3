from core.database import supabase

res = supabase.table("excel_drafts").select("id, sheet_name").execute()
print("Excel Drafts inside Supabase:", res.data)

tab = (
    supabase.table("excel_drafts")
    .select("columns_def, data_rows")
    .eq("sheet_name", "TAB. PRZEBIEG")
    .execute()
)
if tab.data:
    cols = [c.get("field") for c in tab.data[0]["columns_def"]]
    print("\nColumns for 'TAB. PRZEBIEG':", cols)
    if tab.data[0]["data_rows"]:
        print("\nFirst data row:", tab.data[0]["data_rows"][0])
