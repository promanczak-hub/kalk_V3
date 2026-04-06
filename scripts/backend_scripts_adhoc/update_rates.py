import os
import sys

sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()
from core.database import supabase

check = (
    supabase.table("samar_class_depreciation_rates")
    .select("*")
    .eq("samar_class_id", 4)
    .eq("fuel_type_id", 2)
    .execute()
)
print(f"Rows for 4/2: {len(check.data)}")
for c in check.data:
    if c["year"] in [0, 4]:
        print(
            f"year {c['year']}: base={c.get('base_depreciation_percent')}, opt={c.get('options_depreciation_percent')}"
        )
