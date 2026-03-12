"""Check DB rates for samar_class_id=103 (Superb Combi)."""

import sys
import json

sys.path.insert(0, ".")
from core.database import supabase

OUT = "diag_db_output.txt"

with open(OUT, "w", encoding="utf-8") as f:
    # 1. Service rates for class 103
    f.write("=" * 60 + "\n")
    f.write("SERWIS — samar_service_costs (class 103)\n")
    f.write("=" * 60 + "\n")
    r = (
        supabase.table("samar_service_costs")
        .select(
            "samar_class_id,engine_type_id,power_band,cost_aso_per_km,cost_non_aso_per_km"
        )
        .eq("samar_class_id", 103)
        .execute()
    )
    for d in r.data or []:
        f.write(json.dumps(d, indent=2) + "\n")
    if not r.data:
        f.write("  BRAK DANYCH!\n")

    # 2. Insurance rates for class 103
    f.write("\n" + "=" * 60 + "\n")
    f.write("UBEZPIECZENIE — ltr_admin_ubezpieczenia (class 103)\n")
    f.write("=" * 60 + "\n")
    r2 = (
        supabase.table("ltr_admin_ubezpieczenia")
        .select("*")
        .eq("samar_class_id", 103)
        .execute()
    )
    for d in r2.data or []:
        f.write(json.dumps(d, indent=2) + "\n")
    if not r2.data:
        f.write("  BRAK DANYCH!\n")

    # 3. Replacement car rate
    f.write("\n" + "=" * 60 + "\n")
    f.write("SAMOCHOD ZASTEPCZY — replacement_car_rates (class 103)\n")
    f.write("=" * 60 + "\n")
    r3 = (
        supabase.table("replacement_car_rates")
        .select("*")
        .eq("samar_class_id", 103)
        .execute()
    )
    for d in r3.data or []:
        f.write(json.dumps(d, indent=2) + "\n")

    # 4. Damage coefficients
    f.write("\n" + "=" * 60 + "\n")
    f.write("WSP. SZKODOWE — ltr_admin_wspolczynniki_szkodowe (class 103)\n")
    f.write("=" * 60 + "\n")
    r4 = (
        supabase.table("ltr_admin_wspolczynniki_szkodowe")
        .select("*")
        .eq("samar_class_id", 103)
        .execute()
    )
    for d in r4.data or []:
        f.write(json.dumps(d, indent=2) + "\n")

    # 5. All service rates (all classes) — for context
    f.write("\n" + "=" * 60 + "\n")
    f.write("WSZYSTKIE STAWKI SERWISOWE (wszystkie klasy)\n")
    f.write("=" * 60 + "\n")
    r5 = (
        supabase.table("samar_service_costs")
        .select(
            "samar_class_id,engine_type_id,power_band,cost_aso_per_km,cost_non_aso_per_km"
        )
        .execute()
    )
    for d in r5.data or []:
        f.write(
            f"class={d['samar_class_id']} eng={d['engine_type_id']} "
            f"band={d['power_band']} ASO={d['cost_aso_per_km']} "
            f"nonASO={d['cost_non_aso_per_km']}\n"
        )

    # 6. Samar classes — to understand what class 103 is
    f.write("\n" + "=" * 60 + "\n")
    f.write("SAMAR CLASSES — id/name\n")
    f.write("=" * 60 + "\n")
    r6 = supabase.table("samar_classes").select("id, name").execute()
    for d in r6.data or []:
        f.write(f"  id={d['id']}: {d['name']}\n")

    # 7. Control center settings
    f.write("\n" + "=" * 60 + "\n")
    f.write("CONTROL CENTER — ustawienia globalne\n")
    f.write("=" * 60 + "\n")
    try:
        r7 = supabase.table("ltr_admin_parametry").select("*").execute()
        for d in r7.data or []:
            f.write(json.dumps(d, indent=2) + "\n")
    except Exception as e:
        f.write(f"  Error: {e}\n")

print(f"Output zapisany do {OUT}")
