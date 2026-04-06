import os
import sys

sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()
from core.database import supabase

try:
    res = supabase.table("excel_drafts").select("id, sheet_name").limit(1).execute()
    print("SELECT returned:", len(res.data))
    if len(res.data) > 0:
        upd = (
            supabase.table("excel_drafts")
            .update({"sheet_name": res.data[0]["sheet_name"]})
            .eq("id", res.data[0]["id"])
            .execute()
        )
        print("UPDATE returned:", len(upd.data))
except Exception as e:
    print("UPDATE ERROR:", e)
