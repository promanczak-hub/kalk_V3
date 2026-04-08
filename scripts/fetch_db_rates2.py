import sys
import json

sys.path.append(r"d:\kalk_v3\backend")
from core.database import supabase

# 'DSKODAON'
res = supabase.table("samar_classes").select("*").ilike("name", "%DSKODAON%").execute()
if not res.data:
    print("Class not found. Here are all classes:")
    res2 = supabase.table("samar_classes").select("id, name").execute()
    for row in res2.data:
        print(row)
else:
    class_id = res.data[0]["id"]
    print("Class ID:", class_id)
    fuel_id = 2  # ON

    rates = (
        supabase.table("samar_class_depreciation_rates")
        .select("*")
        .eq("samar_class_id", class_id)
        .eq("fuel_type_id", fuel_id)
        .execute()
    )
    print("Rates:", json.dumps(rates.data, indent=2))
    mileage = (
        supabase.table("samar_class_mileage_corrections")
        .select("*")
        .eq("samar_class_id", class_id)
        .eq("fuel_type_id", fuel_id)
        .execute()
    )
    print("Mileage Corrs:", json.dumps(mileage.data, indent=2))
    brand_corr = (
        supabase.table("ltr_admin_korekta_wr_markas")
        .select("*")
        .eq("samar_class_id", class_id)
        .eq("rodzaj_paliwa", fuel_id)
        .execute()
    )
    print("Brand Corrs:", json.dumps(brand_corr.data, indent=2))
