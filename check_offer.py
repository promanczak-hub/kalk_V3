"""Szybka diagnostyka: klasa TERENOWO-REKREACYJNE C + fuel_type benzyna."""

import sys

sys.path.insert(0, "d:/kalk_v3/backend")
from core.database import supabase

# 1. Znajdź dokładne ID klasy TERENOWO-REKREACYJNE C
res = supabase.table("samar_classes").select("id, name").execute()
troc_id = None
for r in res.data or []:
    name = r["name"].strip()
    print(f"  samar_classes id={r['id']:>3}: '{name}'")
    if "TERENOWO-REKREACYJNE C" in name.upper() and "NIŻSZA" in name.upper():
        troc_id = r["id"]
        print(f"  ^^^ MATCH for T-Roc (TERENOWO-REKREACYJNE C NIŻSZA)")

# 2. Jakie fuel_type_id to benzyna PB?
print("\n--- engine_types (fuel types) ---")
try:
    res = supabase.table("engine_types").select("id, name").execute()
    for r in res.data or []:
        print(f"  id={r['id']}: {r['name']}")
except:
    print("  Tabela engine_types nie istnieje, sprawdzam fuel_types...")
    try:
        res = supabase.table("fuel_types").select("id, name").execute()
        for r in res.data or []:
            print(f"  id={r['id']}: {r['name']}")
    except:
        print("  Nie znaleziono tabeli z typami paliw")

# 3. Jeśli znaleźliśmy T-Roc class, pokaż stawki
if troc_id:
    print(f"\n--- Stawki deprecjacji dla klasy ID={troc_id} ---")
    res = (
        supabase.table("samar_class_depreciation_rates")
        .select("*")
        .eq("samar_class_id", troc_id)
        .order("fuel_type_id")
        .order("year")
        .execute()
    )
    print(f"  Rows: {len(res.data or [])}")
    for r in res.data or []:
        print(
            f"  fuel={r['fuel_type_id']}, year={r['year']}, base_depr={r['base_depreciation_percent']}, opts_depr={r['options_depreciation_percent']}"
        )
else:
    print("\n⚠️ Nie znaleziono TERENOWO-REKREACYJNE C NIŻSZA. Szukam z 'C':")
    for r in supabase.table("samar_classes").select("id, name").execute().data or []:
        if " C " in r["name"] or r["name"].strip().endswith(" C"):
            troc_id = r["id"]
            print(f"  Candidate: id={r['id']}, name='{r['name']}'")
