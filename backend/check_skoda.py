from dotenv import load_dotenv

load_dotenv(".env")
from core.database import supabase

res = supabase.table("tabela_rabaty").select("*").limit(100).execute()
for row in res.data:
    marka = str(row.get("marka", "")).lower()
    model = str(row.get("model", "")).lower()
    if "audi" in marka or "a5" in model:
        print(f"{marka.upper()} - {model.upper()} - {row.get('rabat')}")
