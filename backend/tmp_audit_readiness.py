"""Audyt danych w lokalnym Supabase pod kątem Readiness Validator."""

import sys

sys.path.insert(0, ".")
from core.database import supabase
from collections import Counter

SEP = "=" * 60

print(SEP)
print("AUDYT DANYCH - READINESS VALIDATOR")
print(SEP)

# 1. SAMAR Classes
sc = supabase.table("samar_classes").select("id, name, klasa_wr_id").execute()
print(f"\n1. SAMAR CLASSES: {len(sc.data)} klas")
all_class_ids: set[int] = set()
for r in sc.data:
    all_class_ids.add(r["id"])
    wr = r.get("klasa_wr_id", "-")
    print(f"   id={r['id']:3d}  wr={str(wr):>4s}  {r['name']}")

# 2. Engines
eng = supabase.table("engines").select("id, name, category").execute()
print(f"\n2. ENGINES: {len(eng.data)} typow")
all_engine_ids: set[int] = set()
for r in eng.data:
    all_engine_ids.add(r["id"])
    print(f"   id={r['id']:3d}  {r['category']:>12s}  {r['name']}")

# 3. Depreciation Rates
dr = (
    supabase.table("samar_class_depreciation_rates")
    .select("samar_class_id, fuel_type_id, year")
    .execute()
)
print(f"\n3. DEPRECIATION RATES: {len(dr.data)} wierszy")
dr_combos: Counter[tuple[int, int]] = Counter()
for r in dr.data:
    dr_combos[(r["samar_class_id"], r["fuel_type_id"])] += 1
dr_classes = set(k[0] for k in dr_combos)
dr_engines = set(k[1] for k in dr_combos)
missing_dr = all_class_ids - dr_classes
print(f"   Pary (klasa,silnik): {len(dr_combos)}")
print(f"   Klasy BEZ depreciation: {sorted(missing_dr) if missing_dr else 'BRAK - OK'}")
print(
    f"   Silniki BEZ depreciation: {sorted(all_engine_ids - dr_engines) if (all_engine_ids - dr_engines) else 'BRAK - OK'}"
)
# Show only incomplete combos (< 7 years)
incomplete = [(k, v) for k, v in dr_combos.items() if v < 7]
if incomplete:
    print(f"   !!! Niekompletne (<7 lat): {len(incomplete)}")
    for k, v in sorted(incomplete):
        print(f"     class={k[0]:3d} engine={k[1]:3d} => {v} lat")
else:
    print("   Wszystkie kombinacje maja >= 7 lat")

# 4. Insurance Rates
ins = supabase.table("ltr_admin_ubezpieczenia").select("KlasaId, KolejnyRok").execute()
print(f"\n4. INSURANCE RATES: {len(ins.data)} wierszy")
ins_classes = set(r["KlasaId"] for r in ins.data)
print(f"   Pokryte KlasaId: {sorted(ins_classes)}")
missing_ins = all_class_ids - ins_classes
print(
    f"   Klasy BEZ ubezpieczenia: {sorted(missing_ins) if missing_ins else 'BRAK - OK'}"
)

# 5. Service Costs
svc = (
    supabase.table("samar_service_costs")
    .select("samar_class_id, engine_type_id, power_band")
    .execute()
)
print(f"\n5. SERVICE COSTS: {len(svc.data)} wierszy")
svc_combos = set((r["samar_class_id"], r["engine_type_id"]) for r in svc.data)
svc_classes = set(k[0] for k in svc_combos)
missing_svc = all_class_ids - svc_classes
print(f"   Pary (klasa,silnik): {len(svc_combos)}")
print(f"   Klasy BEZ serwisu: {sorted(missing_svc) if missing_svc else 'BRAK - OK'}")

# 6. Replacement Car Rates
rc = (
    supabase.table("replacement_car_rates")
    .select("samar_class_id, daily_rate_net")
    .execute()
)
print(f"\n6. REPLACEMENT CAR RATES: {len(rc.data)} wierszy")
rc_classes = set(r["samar_class_id"] for r in rc.data)
missing_rc = all_class_ids - rc_classes
print(f"   Pokryte klasy: {sorted(rc_classes)}")
print(
    f"   Klasy BEZ auta zastepczego: {sorted(missing_rc) if missing_rc else 'BRAK - OK'}"
)

# 7. Damage Coefficients
try:
    dc = (
        supabase.table("ltr_admin_wspolczynniki_szkodowe")
        .select("klasa_wr_id")
        .execute()
    )
    print(f"\n7. DAMAGE COEFFICIENTS: {len(dc.data)} wierszy")
    dc_classes = set(r["klasa_wr_id"] for r in dc.data)
    print(f"   Pokryte klasy: {sorted(dc_classes)}")
    missing_dc = all_class_ids - dc_classes
    print(
        f"   Klasy BEZ wsp. szkodowych: {sorted(missing_dc) if missing_dc else 'BRAK - OK'}"
    )
except Exception as e:
    print(f"\n7. DAMAGE COEFFICIENTS: BLAD - {e}")

# 8. Tyre Costs
tc = supabase.table("tyre_costs").select("tyre_class, diameter").execute()
print(f"\n8. TYRE COSTS: {len(tc.data)} wierszy")
tyre_classes = set(r["tyre_class"] for r in tc.data)
tyre_diameters = set(r["diameter"] for r in tc.data)
print(f"   Klasy opon: {sorted(tyre_classes)}")
print(f"   Srednice: {sorted(tyre_diameters)}")

# 9. Mileage Corrections
mc = (
    supabase.table("samar_class_mileage_corrections")
    .select("samar_class_id, fuel_type_id")
    .execute()
)
print(f"\n9. MILEAGE CORRECTIONS: {len(mc.data)} wierszy")
mc_classes = set(r["samar_class_id"] for r in mc.data)
missing_mc = all_class_ids - mc_classes
print(
    f"   Klasy BEZ korekty przebiegu: {sorted(missing_mc) if missing_mc else 'BRAK - OK'}"
)

# 10. Control Center
cc = supabase.table("control_center").select("*").eq("id", 1).execute()
print(f"\n10. CONTROL CENTER: {'ISTNIEJE' if cc.data else 'BRAK!!!'}")
if cc.data:
    for k, v in cc.data[0].items():
        if k != "id":
            status = "!!!" if v is None else ""
            print(f"    {k}: {v} {status}")

# 11. Pojazdy Master
pm = (
    supabase.table("pojazdy_master")
    .select("id, klasa_wr_id, engine_type_id, power_kw")
    .execute()
)
print(f"\n11. POJAZDY MASTER: {len(pm.data)} pojazdow")
no_wr = sum(1 for r in pm.data if not r.get("klasa_wr_id"))
no_eng = sum(1 for r in pm.data if not r.get("engine_type_id"))
no_pow = sum(1 for r in pm.data if not r.get("power_kw"))
print(f"    Bez klasa_wr_id: {no_wr}/{len(pm.data)}")
print(f"    Bez engine_type_id: {no_eng}/{len(pm.data)}")
print(f"    Bez power_kw: {no_pow}/{len(pm.data)}")

# 12. Kalkulacje
kl = supabase.table("ltr_kalkulacje").select("id, status, dane_pojazdu").execute()
print(f"\n12. LTR KALKULACJE: {len(kl.data)} kalkulacji")
statuses: Counter[str] = Counter(r.get("status", "?") for r in kl.data)
for s, c in statuses.most_common():
    print(f"    status={s}: {c}")

# Cross-reference check: for each vehicle, which tables are missing?
print(f"\n{SEP}")
print("CROSS-REFERENCE: POJAZD -> BRAKUJACE TABELE")
print(SEP)
for r in pm.data:
    vid = r["id"][:8]
    wr = r.get("klasa_wr_id")
    eid = r.get("engine_type_id")
    issues = []
    if not wr:
        issues.append("klasa_wr_id=NULL")
    elif wr not in ins_classes:
        issues.append(f"brak ubezpieczenia dla klasy {wr}")
    if not wr or wr not in rc_classes:
        issues.append(f"brak auta zastepczego dla klasy {wr}")
    if not wr or wr not in dc_classes:
        issues.append(f"brak wsp.szkodowych dla klasy {wr}")
    if wr and eid and (wr, eid) not in svc_combos:
        issues.append(f"brak serwisu dla klasy={wr} silnik={eid}")
    if wr and eid and (wr, eid) not in set(dr_combos.keys()):
        issues.append(f"brak depreciation dla klasy={wr} silnik={eid}")
    if not eid:
        issues.append("engine_type_id=NULL")
    if not r.get("power_kw"):
        issues.append("power_kw=NULL")
    if issues:
        print(f"  {vid}... : {'; '.join(issues)}")
    else:
        print(f"  {vid}... : OK")

print(f"\n{SEP}")
print("KONIEC AUDYTU")
print(SEP)
