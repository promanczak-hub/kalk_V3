"""Compare matrix output for kalkulacja 56ad9ec0 sent through three paths:

1. Cache row              (already on disk; the UI may be reading this)
2. /api/calculate-matrix with payload built by build_calculator_input (matrix-cache job path)
3. /api/calculate-matrix with stan_json sent verbatim as CalculatorInput   (frontend path)

This pinpoints which payload produces the 3956 PLN/m the user sees in the UI
versus the 2802 PLN/m we saw post-fix.
"""

import json
import sys
import urllib.error
import urllib.request

from core.database import supabase
from core.matrix_cache_job import build_calculator_input
from core.models import ControlCenterSettings

KALK_ID = "56ad9ec0-42e5-4b6c-992d-4a32d18119f5"
VEHICLE_UUID = "701ce3bf-467b-454b-98f1-4e97a615d2d8"


def _post(payload):
    req = urllib.request.Request(
        "http://localhost:8000/api/calculate-matrix",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def _cell(cells, months, total_km):
    return next(
        (c for c in cells if c.get("Okres") == months and c.get("PrzebiegKontrakt") == total_km),
        None,
    )


cc = supabase.table("control_center").select("*").eq("id", 1).execute().data[0]
settings = ControlCenterSettings(**cc)

kalk = supabase.table("ltr_kalkulacje").select("*").eq("id", KALK_ID).execute().data[0]
stan = kalk["stan_json"]
print(f"Kalkulacja: {kalk['numer_kalkulacji']} (id={KALK_ID})")
print(f"  stan_json.base_price_net   : {stan.get('base_price_net')!r}")
print(f"  stan_json.discount_pct     : {stan.get('discount_pct')!r}")
print(f"  stan_json.pricing_margin   : {stan.get('pricing_margin_pct')!r}")
print(f"  stan_json.paint_type_name  : {stan.get('paint_type_name')!r}")
print(f"  stan_json.is_metalic       : {stan.get('is_metalic')!r}")
print(f"  stan_json.paint_category_id: {stan.get('paint_category_id')!r}")

# ── PATH 1: cache values (raw)
print("\n=== PATH 1: vehicle_matrix_cache (raw row stored) ===")
rows = (
    supabase.table("vehicle_matrix_cache")
    .select("duration_months,annual_mileage,monthly_price_net,base_price_net,discount_pct,calculated_at")
    .eq("kalkulacja_id", KALK_ID)
    .in_("duration_months", [24, 36, 48, 60])
    .in_("annual_mileage", [30000])
    .order("duration_months")
    .execute()
).data
for r in rows:
    print(f"  Okres={r['duration_months']}, annual={r['annual_mileage']} -> monthly_net={r['monthly_price_net']} (base={r['base_price_net']}, disc={r['discount_pct']}%, at {r['calculated_at']})")

# ── PATH 2: rebuild via build_calculator_input (matrix-cache path)
print("\n=== PATH 2: POST /api/calculate-matrix with build_calculator_input(vehicle) ===")
v = supabase.table("vehicle_synthesis").select("*").eq("id", VEHICLE_UUID).execute().data[0]
inp2 = build_calculator_input(v, margin_pct=0.0, settings=settings)
payload2 = json.loads(inp2.model_dump_json())
print(f"  payload.base_price_net   : {payload2['base_price_net']}")
print(f"  payload.paint_type_name  : {payload2.get('paint_type_name')!r}")
print(f"  payload.discount_pct     : {payload2['discount_pct']}")

resp2 = _post(payload2)
c2 = _cell(resp2["cells"], 48, 120000)
if c2:
    print(f"  cell 48m/120k: WR_net={c2['WR']:.2f}  LacznaStawka={c2['LacznaStawka']}  CenaZakupu={c2['CenaZakupu']:.2f}")
else:
    print("  no 48m/120k cell")

# ── PATH 3: build payload like frontend useVehicleCalculations.fetchMatrix does
print("\n=== PATH 3: POST /api/calculate-matrix with frontend-style payload ===")

cs_top = stan.get("card_summary") or {}
fp     = stan.get("financial_params") or {}
tg     = stan.get("toggles") or {}
mai    = stan.get("mapped_ai_data") or {}
disc   = stan.get("discount") or {}
sd     = stan.get("synthesis_data") or {}
cs_sd  = sd.get("card_summary") or {}
setup  = sd.get("calculator_setup") or {}
pp     = cs_sd.get("parsed_prices") or {}
uf     = sd.get("universal_features") or {}
comp   = sd.get("computed") or {}

# Robust price discovery, mirroring useVehicleCalculations.ts:159-173
raw_base = (
    setup.get("catalog_base_price_net")
    or cs_top.get("base_price")
    or cs_top.get("total_price")
    or pp.get("base")
    or uf.get("cena_pojazdu")
    or comp.get("estimated_price")
    or "0"
)
raw_base_str = str(raw_base)
import re as _re
clean_str = _re.sub(r"\s+", "", raw_base_str.replace(",", "."))
clean_str = _re.sub(r"[^0-9.]", "", clean_str)
clean = float(clean_str or 0)
price_domain = (cs_top.get("_price_domain") or cs_top.get("price_domain") or "unknown").lower()
is_brutto = "brutto" in raw_base_str.lower() or price_domain == "brutto"
base_net_fe = round(clean / 1.23, 2) if is_brutto else clean

okres_bazowy_fe   = mai.get("usage_months") or 48
przebieg_bazowy_fe = mai.get("total_km") or 140000

factory_options = [
    {
        "name": o.get("name") or "Opcja",
        "price_net": o.get("price_net") or 0,
        "price_gross": o.get("price_gross") or round((o.get("price_net") or 0) * 1.23, 2),
        "no_discount": bool(o.get("no_discount")),
        "include_in_wr": False,
    }
    for o in (stan.get("factory_options") or [])
]
service_options = [
    {
        "name": o.get("name") or "Usluga",
        "price_net": o.get("price_net") or 0,
        "price_gross": o.get("price_gross") or round((o.get("price_net") or 0) * 1.23, 2),
        "no_discount": False,
        "include_in_wr": bool(o.get("include_in_wr")),
    }
    for o in (stan.get("service_options") or [])
]

frontend_payload = {
    "vehicle_id": stan.get("vehicle_id") or VEHICLE_UUID,
    "base_price_net": base_net_fe,
    "discount_pct": (disc.get("active_discount_pct") or 0),
    "factory_options": factory_options,
    "service_options": service_options,
    "okres_bazowy": okres_bazowy_fe,
    "przebieg_bazowy": przebieg_bazowy_fe,
    "wibor_pct": fp.get("wibor_pct"),
    "margin_pct": fp.get("margin_pct"),
    "depreciation_pct": fp.get("depreciation_pct") or None,
    "initial_deposit_pct": fp.get("initial_deposit_pct") or 0,
    "replacement_car_enabled": tg.get("replacement_car") is not False,
    "add_gsm_subscription": tg.get("gps_required") is not False,
    "add_hook_installation": tg.get("hook_installation") is True,
    "add_sales_prep": tg.get("add_sales_prep") is not False,
    "express_pays_insurance": tg.get("express_pays_insurance") is not False,
    "z_oponami": (tg.get("include_tires") or tg.get("z_oponami")) is not False,
    "klasa_opony_string": (stan.get("tire_params") or {}).get("tire_class") or "Medium",
    "srednica_felgi": (stan.get("tire_params") or {}).get("rim_diameter") or 16,
    "service_cost_type": stan.get("service_cost_type") or "ASO",
    "include_servicing": tg.get("include_servicing") is not False,
    "vehicle_vintage": stan.get("vehicle_vintage") or "current",
    "is_metalic": stan.get("is_metalic") is True,
    "pricing_margin_pct": fp.get("pricing_margin_pct") if fp.get("pricing_margin_pct") is not None else 0,
    "manual_wr_correction": 0,
    "inne_koszty_serwisowania_netto": float(fp.get("other_service_costs") or 0),
    "matrix_km_mode": "annual",
    "matrix_contract_km_step": 10000,
    "power_kw": stan.get("power_kw") or cs_top.get("power_kw") or 0,
    "paint_type_name": (mai.get("color") or stan.get("typ_lakieru") or stan.get("paint_type_name") or cs_top.get("color") or ""),
    "body_type_name": (mai.get("body_type") or stan.get("body_type_name") or cs_top.get("body_style") or ""),
    "samar_category": (mai.get("samar_category") or stan.get("samar_category") or cs_top.get("samar_category") or ""),
    "engine_name": (mai.get("fuel") or stan.get("engine_category") or cs_top.get("engine_category") or cs_top.get("powertrain") or ""),
}
print(f"  payload.base_price_net   : {frontend_payload['base_price_net']}")
print(f"  payload.paint_type_name  : {frontend_payload['paint_type_name']!r}")
print(f"  payload.is_metalic       : {frontend_payload['is_metalic']!r}")
print(f"  payload.discount_pct     : {frontend_payload['discount_pct']}")

try:
    resp3 = _post(frontend_payload)
    cells = resp3["cells"]
    print(f"  cells returned: {len(cells)}")
    for (m, k) in [(24, 120000), (36, 120000), (48, 120000), (60, 120000)]:
        c = _cell(cells, m, k)
        if c:
            print(f"  cell {m}m/{k//1000}k: WR_net={c['WR']:.2f}  LacznaStawka={c['LacznaStawka']}  CenaZakupu={c['CenaZakupu']:.2f}")
        else:
            print(f"  cell {m}m/{k//1000}k: MISSING")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}: {e.read().decode()[:800]}", file=sys.stderr)
    raise SystemExit(1)

# ── Compare cost breakdown for 48m/120k between Path 2 and Path 3
print("\n=== COST BREAKDOWN @ 48m/120k: Path 2 (matrix-cache) vs Path 3 (frontend) ===")
resp2 = _post(payload2)
c2 = _cell(resp2["cells"], 48, 120000)
c3 = _cell(_post(frontend_payload)["cells"], 48, 120000)
keys = ["WR", "LacznaStawka", "CzynszFinansowy", "CzynszTechniczny",
        "Ubezpieczenie", "Serwis", "Opony", "SamochodZastepczy", "Admin",
        "MarzaNaKontrakcie", "CenaZakupu", "GsmCapexNetto", "OpcjeSerwisoweSumaNetto"]
for k in keys:
    v2 = c2.get(k); v3 = c3.get(k)
    diff = (v3 - v2) if (isinstance(v2,(int,float)) and isinstance(v3,(int,float))) else "?"
    print(f"  {k:>30}: P2={v2!r:>12}  P3={v3!r:>12}  Δ={diff!r}")

# ── Toggle comparison
print("\n=== TOGGLE / FIELD COMPARISON (Path 2 vs Path 3 payloads) ===")
fields = ["z_oponami", "include_servicing", "replacement_car_enabled",
          "express_pays_insurance", "add_hook_installation", "add_gsm_subscription",
          "add_sales_prep", "klasa_opony_string", "srednica_felgi",
          "service_cost_type", "vehicle_vintage", "is_metalic",
          "paint_type_name", "samar_category", "engine_name", "body_type_name",
          "discount_pct", "pricing_margin_pct", "wibor_pct", "margin_pct",
          "initial_deposit_pct", "inne_koszty_serwisowania_netto",
          "matrix_km_mode"]
for f in fields:
    v2 = payload2.get(f); v3 = frontend_payload.get(f)
    flag = "" if v2 == v3 else "  ⚠"
    print(f"  {f:>32}: P2={v2!r:>30}  P3={v3!r:>30}{flag}")
