import os
import sys
sys.path.append(r"d:\kalk_v3\backend")
from core.database import supabase

# We need to update samar_class_depreciation_rates
# class_id = 103, fuel_type_id = 2, year = 4
# set options_depreciation_percent = 0.26

class_id = 103
fuel_id = 2
year = 4
new_rate = 0.26

print(f"Updating class {class_id} fuel {fuel_id} year {year} options_depreciation_percent to {new_rate}...")

res = supabase.table("samar_class_depreciation_rates").update(
    {"options_depreciation_percent": new_rate}
).eq("samar_class_id", class_id).eq("fuel_type_id", fuel_id).eq("year", year).execute()

print("Update result:", res.data)

# Let's also check if year 5, 6, 7 should be shifted, but for now we just fix year 4 as discussed.
