from core.database import supabase

res = (
    supabase.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB. PRZEBIEG")
    .execute()
)
if res.data and res.data[0]["data_rows"]:
    for r in res.data[0]["data_rows"][:10]:
        print(r)
