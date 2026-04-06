import asyncio
from core.database import supabase
import sys

res = supabase.table("samar_class_mileage_corrections").select("samar_class_id, fuel_type_id").execute()
existing = {(r['samar_class_id'], r['fuel_type_id']) for r in res.data}
with open("missing.log", "w") as f:
    f.write(f"Class 10, Fuel 3 exists: {(10, 3) in existing}\n")
