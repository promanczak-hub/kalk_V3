import os
import sys
import json
sys.path.append(r"d:\kalk_v3\backend")

from core.database import supabase

# D_SKODA_ON - we need to see what samar_class_id it is.
# Fuel ON is 2.
samar_class_res = supabase.table("samar_classes").select("id, name").ilike("name", "%SKODA%").execute()
classes = samar_class_res.data
print("Classes:", json.dumps(classes, indent=2))

class_id = None
for c in classes:
    if 'D_SKODA' in c['name'] or 'D SKODA' in c['name'] or 'D' in c['name'] and 'SKODA' in c['name']:
        class_id = c['id']

if not class_id:
    # Let's search by name
    res2 = supabase.table("samar_classes").select("id, name").execute()
    for c in res2.data:
        if 'D' in c['name'].upper() and 'SKODA' in c['name'].upper():
            print("Found:", c)
            class_id = c['id']

print("Using class_id:", class_id)
if class_id:
    fuel_id = 2 # ON
    rates = supabase.table("samar_class_depreciation_rates").select("*").eq("samar_class_id", class_id).eq("fuel_type_id", fuel_id).execute()
    print("Rates:", json.dumps(rates.data, indent=2))
    
    mileage = supabase.table("samar_class_mileage_corrections").select("*").eq("samar_class_id", class_id).eq("fuel_type_id", fuel_id).execute()
    print("Mileage Corrs:", json.dumps(mileage.data, indent=2))
    
    brand_corr = supabase.table("ltr_admin_korekta_wr_markas").select("*").eq("samar_class_id", class_id).eq("rodzaj_paliwa", fuel_id).execute()
    print("Brand Corrs:", json.dumps(brand_corr.data, indent=2))
    
    config = supabase.table("samar_classes").select("*").eq("id", class_id).execute()
    print("Config:", json.dumps(config.data, indent=2))

