"""End-to-end check that the resolver endpoint produces a CalculatorInput
that, when posted verbatim to /api/calculate-matrix, gives the same answer
as the legacy build_calculator_input path AND the cache.

Three calls, all hitting the live backend:
  A) GET resolved input from /api/calculator/resolve-input
  B) POST that resolved input to /api/calculate-matrix
  C) compare to direct build_calculator_input + /api/calculate-matrix
"""

import json
import sys
import urllib.error
import urllib.request

from core.database import supabase
from core.matrix_cache_job import build_calculator_input
from core.models import ControlCenterSettings

VEHICLE_UUID = "701ce3bf-467b-454b-98f1-4e97a615d2d8"
KALK_ID = "56ad9ec0-42e5-4b6c-992d-4a32d18119f5"
EXPECTED_WR_NET = 66_004.69


def _post(path, payload):
    req = urllib.request.Request(
        f"http://localhost:8000{path}",
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


# --- A) hit /api/calculator/resolve-input
print("=== /api/calculator/resolve-input — vehicle only ===")
resp_a = _post("/api/calculator/resolve-input", {"vehicle_id": VEHICLE_UUID, "margin_pct": 0.0})
ci_a = resp_a["calculator_input"]
print(f"  base_price_net : {ci_a['base_price_net']}")
print(f"  paint_type_id  : {ci_a.get('paint_type_id')}")
print(f"  paint_type_name: {ci_a.get('paint_type_name')!r}")
print(f"  is_metalic     : {ci_a['is_metalic']}")
print(f"  discount_pct   : {ci_a['discount_pct']}")
print(f"  pricing_margin_pct: {ci_a['pricing_margin_pct']}")
print(f"  factory_options: {len(ci_a['factory_options'])} items, sum_net={sum(o['price_net'] for o in ci_a['factory_options']):.2f}")

# B) feed that into /api/calculate-matrix
resp_a_matrix = _post("/api/calculate-matrix", ci_a)
cell_a = _cell(resp_a_matrix["cells"], 48, 120000)
print(f"\n=== matrix cell 48m/120k from resolver-only payload ===")
print(f"  WR_net       : {cell_a['WR']:.2f}  (expected {EXPECTED_WR_NET})")
print(f"  LacznaStawka : {cell_a['LacznaStawka']}")
print(f"  CenaZakupu   : {cell_a['CenaZakupu']:.2f}")

# Compare with direct build path
cc = supabase.table("control_center").select("*").eq("id", 1).execute().data[0]
settings = ControlCenterSettings(**cc)
v = supabase.table("vehicle_synthesis").select("*").eq("id", VEHICLE_UUID).execute().data[0]
inp_direct = build_calculator_input(v, margin_pct=0.0, settings=settings)
resp_direct = _post("/api/calculate-matrix", json.loads(inp_direct.model_dump_json()))
cell_direct = _cell(resp_direct["cells"], 48, 120000)
print(f"\n=== matrix cell 48m/120k from direct build_calculator_input ===")
print(f"  WR_net       : {cell_direct['WR']:.2f}")
print(f"  LacznaStawka : {cell_direct['LacznaStawka']}")
print(f"  CenaZakupu   : {cell_direct['CenaZakupu']:.2f}")

# Resolver with kalkulacja overlay
print("\n=== /api/calculator/resolve-input — vehicle + kalkulacja overlay ===")
resp_b = _post(
    "/api/calculator/resolve-input",
    {"vehicle_id": VEHICLE_UUID, "kalkulacja_id": KALK_ID, "margin_pct": 0.0},
)
ci_b = resp_b["calculator_input"]
print(f"  base_price_net : {ci_b['base_price_net']}")
print(f"  paint_type_id  : {ci_b.get('paint_type_id')}")
print(f"  is_metalic     : {ci_b['is_metalic']}")
print(f"  pricing_margin : {ci_b['pricing_margin_pct']}")

resp_b_matrix = _post("/api/calculate-matrix", ci_b)
cell_b = _cell(resp_b_matrix["cells"], 48, 120000)
print(f"\n=== matrix cell 48m/120k from resolver+kalkulacja overlay ===")
print(f"  WR_net       : {cell_b['WR']:.2f}")
print(f"  LacznaStawka : {cell_b['LacznaStawka']}")
print(f"  CenaZakupu   : {cell_b['CenaZakupu']:.2f}")

# Resolver with overrides
print("\n=== /api/calculator/resolve-input — overrides ===")
resp_c = _post(
    "/api/calculator/resolve-input",
    {
        "vehicle_id": VEHICLE_UUID,
        "margin_pct": 5.0,
        "overrides": {"add_hook_installation": False, "include_servicing": False},
    },
)
ci_c = resp_c["calculator_input"]
print(f"  pricing_margin_pct  : {ci_c['pricing_margin_pct']}  (expected 5.0)")
print(f"  add_hook_installation: {ci_c['add_hook_installation']}  (expected False)")
print(f"  include_servicing   : {ci_c['include_servicing']}  (expected False)")

# Verdict
ok_resolver = abs(cell_a["WR"] - EXPECTED_WR_NET) < 1.0
ok_direct = abs(cell_direct["WR"] - EXPECTED_WR_NET) < 1.0
ok_match = abs(cell_a["WR"] - cell_direct["WR"]) < 0.01 and cell_a["LacznaStawka"] == cell_direct["LacznaStawka"]
ok_overlay = abs(cell_b["WR"] - EXPECTED_WR_NET) < 1.0

print("\n=== VERDICT ===")
print(f"  resolver-only WR matches Excel : {ok_resolver}")
print(f"  direct        WR matches Excel : {ok_direct}")
print(f"  resolver == direct (parity)    : {ok_match}")
print(f"  resolver+overlay WR matches    : {ok_overlay}")
print(f"  override pricing_margin_pct=5  : {ci_c['pricing_margin_pct'] == 5.0}")
print(f"  override toggles applied       : {ci_c['add_hook_installation'] is False and ci_c['include_servicing'] is False}")
all_ok = ok_resolver and ok_direct and ok_match and ok_overlay
print(f"\n  OVERALL: {'PASS' if all_ok else 'FAIL'}")
sys.exit(0 if all_ok else 1)
