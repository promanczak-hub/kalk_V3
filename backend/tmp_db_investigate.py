"""Investigate all DB tables relevant for V3 calculator validation."""

import json
from core.database import supabase

vehicle_id = "00b6b89a-d2d7-430d-b298-2d7032f98032"

# 1. Vehicle synthesis — all columns
print("=" * 60)
print("1. VEHICLE SYNTHESIS (all columns)")
print("=" * 60)
v = supabase.table("vehicle_synthesis").select("*").eq("id", vehicle_id).execute()
if v.data:
    row = v.data[0]
    # Print all except synthesis_data (too big)
    for k, val in sorted(row.items()):
        if k == "synthesis_data":
            continue
        print(f"  {k}: {val}")
else:
    print("  NOT FOUND")

# 1b. Check synthesis_data.card_summary
print("\n" + "=" * 60)
print("1b. CARD SUMMARY from synthesis_data")
print("=" * 60)
if v.data:
    sd = v.data[0].get("synthesis_data") or {}
    cs = sd.get("card_summary") or {}
    for k, val in sorted(cs.items()):
        if isinstance(val, (dict, list)):
            print(f"  {k}: {json.dumps(val, default=str)[:200]}")
        else:
            print(f"  {k}: {val}")

# 2. Tire prices
print("\n" + "=" * 60)
print("2. TIRE PRICES")
print("=" * 60)
tp = supabase.table("tire_prices").select("*").execute()
if tp.data:
    for row in tp.data:
        print(f"  {json.dumps(row, default=str)}")
else:
    print("  NO DATA")

# 3. Service rates
print("\n" + "=" * 60)
print("3. SERVICE RATES")
print("=" * 60)
try:
    sr = supabase.table("service_rates").select("*").execute()
    if sr.data:
        for row in sr.data[:20]:
            print(f"  {json.dumps(row, default=str)}")
    else:
        print("  NO DATA")
except Exception as e:
    print(f"  ERROR: {e}")

# 4. SAMAR classes
print("\n" + "=" * 60)
print("4. SAMAR CLASSES")
print("=" * 60)
try:
    sc = supabase.table("samar_classes").select("*").execute()
    if sc.data:
        for row in sc.data:
            print(f"  {json.dumps(row, default=str)}")
    else:
        print("  NO DATA")
except Exception as e:
    print(f"  ERROR: {e}")

# 5. Replacement car rates
print("\n" + "=" * 60)
print("5. REPLACEMENT CAR RATES")
print("=" * 60)
try:
    rc = supabase.table("replacement_car_rates").select("*").execute()
    if rc.data:
        for row in rc.data:
            print(f"  {json.dumps(row, default=str)}")
    else:
        print("  NO DATA")
except Exception as e:
    print(f"  ERROR: {e}")

# 6. Control center
print("\n" + "=" * 60)
print("6. CONTROL CENTER")
print("=" * 60)
cc = supabase.table("control_center").select("*").eq("id", 1).execute()
if cc.data:
    for k, val in sorted(cc.data[0].items()):
        print(f"  {k}: {val}")

# 7. samar_klasa_wr
print("\n" + "=" * 60)
print("7. SAMAR KLASA WR")
print("=" * 60)
try:
    skw = supabase.table("samar_klasa_wr").select("*").execute()
    if skw.data:
        for row in skw.data:
            print(f"  {json.dumps(row, default=str)}")
    else:
        print("  NO DATA")
except Exception as e:
    print(f"  ERROR: {e}")

# 8. Insurance rates
print("\n" + "=" * 60)
print("8. INSURANCE RATES (sample)")
print("=" * 60)
try:
    ir = supabase.table("ltr_admin_ubezpieczenia").select("*").limit(5).execute()
    if ir.data:
        for row in ir.data:
            print(f"  {json.dumps(row, default=str)}")
    else:
        print("  NO DATA")
except Exception as e:
    print(f"  ERROR: {e}")
