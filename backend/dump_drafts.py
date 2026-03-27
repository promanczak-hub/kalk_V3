import os
import sys

sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()
from core.database import supabase

# 1. Get drafts
c = (
    supabase.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB. OKRES FINAL")
    .execute()
)
rows = c.data[0]["data_rows"]

# 2. Find row for D ŚREDNIA Diesel (ON)
for r in rows:
    v = r.get("klasa_samar", r.get("col_1", ""))
    if "ŚREDNIA" in v and "ON" in v:
        print("draft OKRES FINAL for year 4:", r.get("rok_4", r.get("col_5")))

c2 = (
    supabase.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB. PRZEBIEG")
    .execute()
)
rows2 = c2.data[0]["data_rows"]
for r in rows2:
    v = r.get("klasa_samar", r.get("col_1", ""))
    if "ŚREDNIA" in v and "ON" in v:
        print("draft PRZEBIEG:", r)

c3 = (
    supabase.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB.WR KLASA")
    .execute()
)
rows3 = c3.data[0]["data_rows"]
for r in rows3:
    v = r.get("klasa_samar", r.get("col_1", ""))
    if "ŚREDNIA" in v and "ON" in v:
        print("draft WR KLASA (yr0 base):", r.get("col_2"))
