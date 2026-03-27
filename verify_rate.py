import os
import sys
import json
sys.path.append(r"d:\kalk_v3\backend")
from core.database import supabase

res = supabase.table("samar_class_depreciation_rates").select("*").eq("samar_class_id", 103).eq("fuel_type_id", 2).eq("year", 4).execute()
print(res.data)
