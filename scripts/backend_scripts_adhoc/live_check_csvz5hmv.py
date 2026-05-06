"""End-to-end live-API check: hit the running /calculate-matrix endpoint
exactly like the frontend does, for CSVZ5HMV at margin 0%, and verify WR
matches Excel row 1683 (66 004.69 PLN net / 81 185.76 PLN brutto / 36.42 %).
"""

import json
import sys
import urllib.error
import urllib.request

from core.database import supabase
from core.matrix_cache_job import build_calculator_input
from core.models import ControlCenterSettings

VEHICLE_UUID = "701ce3bf-467b-454b-98f1-4e97a615d2d8"
EXPECTED_WR_NET = 66_004.69
EXPECTED_WR_GROSS = 81_185.76
EXPECTED_WR_PCT = 0.3642

cc = supabase.table("control_center").select("*").eq("id", 1).execute().data[0]
settings = ControlCenterSettings(**cc)
v = (
    supabase.table("vehicle_synthesis")
    .select("*")
    .eq("id", VEHICLE_UUID)
    .execute()
    .data[0]
)
inp = build_calculator_input(v, margin_pct=0.0, settings=settings)

print(f"vehicle         : {v['brand']} {v['model']} (config_code={v['synthesis_data'].get('configuration_code')})")
print(f"paint_type_name : {inp.paint_type_name!r}")
print(f"is_metalic      : {inp.is_metalic!r}")

payload = json.loads(inp.model_dump_json())
req = urllib.request.Request(
    "http://localhost:8000/api/calculate-matrix",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:800]}", file=sys.stderr)
    sys.exit(1)

cells = body.get("cells", [])
print(f"\ncells returned   : {len(cells)}")

target = next(
    (c for c in cells if c.get("Okres") == 48 and c.get("PrzebiegKontrakt") == 120000),
    None,
)
if not target:
    sample = [(c.get("Okres"), c.get("PrzebiegKontrakt")) for c in cells[:5]]
    print(f"no 48m/120k cell — sample: {sample}")
    sys.exit(2)

vat = float(getattr(settings, "vat_rate", 1.23) or 1.23)
if vat > 10.0:
    vat = 1.0 + (vat / 100.0)

wr_net = float(target["WR"])
wr_gross = wr_net * vat
sum_net = inp.base_price_net + sum(o.price_net for o in inp.factory_options)
wr_pct = wr_net / sum_net

print("\n=== LIVE /calculate-matrix — Okres=48, PrzebiegKontrakt=120000 ===")
print(f"  WR (net)     : {wr_net:>12,.2f} PLN  (expected {EXPECTED_WR_NET:,.2f}, diff {wr_net - EXPECTED_WR_NET:+.2f})")
print(f"  WR (gross)   : {wr_gross:>12,.2f} PLN  (expected {EXPECTED_WR_GROSS:,.2f}, diff {wr_gross - EXPECTED_WR_GROSS:+.2f})")
print(f"  WR %         : {wr_pct * 100:>11.2f} %    (expected {EXPECTED_WR_PCT * 100:.2f} %)")
print(f"  WRdlaLO      : {target.get('WRdlaLO'):>12,.2f} PLN")
print(f"  LacznaStawka : {target.get('LacznaStawka'):>12,.2f} PLN  (margin 0%)")
print(f"  CenaZakupu   : {target.get('CenaZakupu'):>12,.2f}")
print(f"  Marża        : {target.get('MarzaNaKontrakcie'):>12,.2f} PLN")

ok_net = abs(wr_net - EXPECTED_WR_NET) < 1.0
ok_pct = abs(wr_pct - EXPECTED_WR_PCT) < 0.001
print(f"\n  WR net match: {ok_net}")
print(f"  WR pct match: {ok_pct}")
print(f"  VERDICT     : {'PASS' if ok_net and ok_pct else 'FAIL'}")
sys.exit(0 if (ok_net and ok_pct) else 3)
