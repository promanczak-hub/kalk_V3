import os
import sys
from dotenv import load_dotenv

load_dotenv()
# Set path to backend
sys.path.insert(0, os.path.abspath("."))
from core.database import supabase
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew

calc_id = "952946f5-5989-479b-b9fe-3d31a41c6933"

res = supabase.table("ltr_kalkulacje").select("*").eq("id", calc_id).execute()
if not res.data:
    print("Kalkulacja not found")
    sys.exit(1)

import json

calc = res.data[0]
dane_raw = calc.get("dane_pojazdu")
try:
    if isinstance(dane_raw, str) and dane_raw.strip():
        vehicle = json.loads(dane_raw)
    else:
        vehicle = dane_raw or {}
except Exception:
    vehicle = {}

if not vehicle:
    stan_raw = calc.get("stan_json")
    try:
        if isinstance(stan_raw, str) and stan_raw.strip():
            stan = json.loads(stan_raw)
        else:
            stan = stan_raw or {}
    except Exception:
        stan = {}
    vehicle = stan.get("dane_pojazdu", {})
    calc_input = stan
else:
    stan_raw = calc.get("stan_json")
    if isinstance(stan_raw, str):
        calc_input = json.loads(stan_raw)
    else:
        calc_input = stan_raw or {}

# Fallback values if missing
base_price = (
    vehicle.get("base_price")
    or vehicle.get("Ceny", {}).get("CenaPodstawowaBrutto")
    or 201504.07
)
options_price = (
    vehicle.get("options_price")
    or vehicle.get("Ceny", {}).get("CenaOpcjiBrutto")
    or 28211.38
)
vat = 1.23
base_net = float(base_price) / vat
options_net = float(options_price) / vat

if not vehicle.get("samar_class_id") and not vehicle.get("Segment"):
    vehicle["Segment"] = "Podstawowa - D ŚREDNIA"
    vehicle["samar_class_id"] = 4  # typical class id, will rely on Segment
if not vehicle.get("engine_type_id"):
    vehicle["engine_type_id"] = 9  # diesel

samar_id = vehicle.get("samar_class_id") or 1
print(
    f"Vehicle: {vehicle.get('Marka', 'SKODA')} {vehicle.get('Model', 'Superb')} {vehicle.get('Wersja', '')} Class: {samar_id}"
)
print(f"Base Net: {base_net:.2f}, Options Net: {options_net:.2f}")
print(f"Total Net: {(base_net + options_net):.2f}")

try:
    rv_node = LTRSubCalculatorUtrataWartosciNew(vehicle, calc_input)
    res_val = rv_node.calculate_values(
        48, 140000, float(base_price), float(options_price)
    )

    print(f"\\nWR_Netto: {res_val['WR']:.2f}")
    print(f"WR_Gross: {res_val['WR_Gross']:.2f}")
    print(f"WR_Percent: {res_val['WR_percent'] * 100:.2f}%")
    print("\\nTRACE:")
    for t in res_val["trace"]:
        print(f"{t['krok']}: {t['wynik']:.2f} ({t['rownanie']})")
except Exception:
    import traceback

    traceback.print_exc()
