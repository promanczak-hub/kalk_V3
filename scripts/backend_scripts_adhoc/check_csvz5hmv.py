"""Verify legacy WR matches Excel row 1683 for vehicle CSVZ5HMV (SKODA Octavia RS).

Reference (from email screenshot / Excel row 1683 of 2503_wynik_JL.xlsx):
  WR netto  = 66 004.69 PLN
  WR brutto = 81 185.76 PLN
  WR %      = 36.42 %
  Contract  : 48 m / 120k km, marza 0%
"""

from core.database import supabase
from core.matrix_cache_job import build_calculator_input
from core.models import ControlCenterSettings
from core.LTRKalkulator import LTRKalkulator

VEHICLE_UUID = "701ce3bf-467b-454b-98f1-4e97a615d2d8"
EXPECTED_WR_NET = 66_004.69
EXPECTED_WR_GROSS = 81_185.76
EXPECTED_WR_PCT = 0.3642

# 1) settings
cc = supabase.table("control_center").select("*").eq("id", 1).execute().data[0]
settings = ControlCenterSettings(**cc)
vat = float(getattr(settings, "vat_rate", 1.23) or 1.23)
if vat > 10.0:
    vat = 1.0 + (vat / 100.0)

# 2) vehicle
v = (
    supabase.table("vehicle_synthesis")
    .select("*")
    .eq("id", VEHICLE_UUID)
    .execute()
    .data[0]
)
sd = v["synthesis_data"]
print(
    f"Vehicle: {v['brand']} {v['model']} (config_code={sd.get('configuration_code')!r})"
)
cs = sd.get("card_summary", {})
print(
    f"  trim={cs.get('trim_level')}, body={cs.get('body_style')}, "
    f"fuel={cs.get('engine_category')}, metalic={cs.get('is_metalic_paint')}"
)

# 3) calculator input @ margin 0%
inp = build_calculator_input(v, margin_pct=0.0, settings=settings)
if not inp:
    raise SystemExit("build_calculator_input returned None")

fact_opts_net = sum(o.price_net for o in inp.factory_options)
print(
    f"\nCalculatorInput: base_net={inp.base_price_net:.2f}, "
    f"factory_opts_net={fact_opts_net:.2f}, "
    f"sum_net={(inp.base_price_net + fact_opts_net):.2f}, "
    f"sum_brutto={(inp.base_price_net + fact_opts_net) * vat:.2f}"
)

# 4) build matrix and pick the 48m / 120k km cell
calc = LTRKalkulator(input_data=inp, settings=settings)
cells = calc.build_matrix()

target = next(
    (
        c
        for c in cells
        if c.get("Okres") == 48 and c.get("PrzebiegKontrakt") == 120000
    ),
    None,
)
if not target:
    print("\n48m cells available (Okres=48):")
    for c in cells:
        if c.get("Okres") == 48:
            print(
                f"  Przebieg={c.get('Przebieg')}, PrzebiegKontrakt={c.get('PrzebiegKontrakt')}, WR={c.get('WR')}"
            )
    raise SystemExit("no cell with Okres=48 and PrzebiegKontrakt=120000")

wr_net = float(target["WR"])
wr_gross = wr_net * vat
wr_pct = wr_net / (inp.base_price_net + fact_opts_net)

print(f"\n=== MATRIX CELL (Okres=48, Przebieg/year={target['Przebieg']}, KontraktKm=120000) ===")
print(f"  WR (net)    : {wr_net:>12,.2f} PLN  (expected {EXPECTED_WR_NET:,.2f}, diff {wr_net - EXPECTED_WR_NET:+.2f})")
print(f"  WR (gross)  : {wr_gross:>12,.2f} PLN  (expected {EXPECTED_WR_GROSS:,.2f}, diff {wr_gross - EXPECTED_WR_GROSS:+.2f})")
print(f"  WR %        : {wr_pct * 100:>11.2f} %    (expected {EXPECTED_WR_PCT * 100:.2f} %)")
print(f"  WRdlaLO     : {target.get('WRdlaLO'):>12,.2f} PLN")
print(f"  UtrataWartosci: {target.get('UtrataWartosci'):>10,.2f} PLN")

# 5) Re-run the SamarRV layer directly to expose the 6-step debug trace
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew

rv_calc = LTRSubCalculatorUtrataWartosciNew(calc.vehicle, inp)
rv_res = rv_calc.calculate_values(
    months=48,
    total_km=120_000,
    base_vehicle_catalog_gross=inp.base_price_net * vat,
    options_catalog_gross=fact_opts_net * vat,
)
d = rv_res["debug"]
print("\n=== 6-step trace (samar_rv.py debug) ===")
print(f"  krok1 effective_pct        : {d.get('krok1_effective_pct')}")
print(f"  krok1 brand_correction     : {d.get('krok1_brand_correction')}")
print(f"  krok1 wr_base_netto        : {d.get('krok1_wr_value_netto')}")
print(f"  krok3 rv_options_netto     : {d.get('krok3_rv_options_netto')}")
print(f"  krok3 rv_total_netto       : {d.get('krok3_rv_total_netto')}")
print(f"  krok4 korekta_przebieg_net : {d.get('krok4_korekta_przebieg_netto')}")
print(f"  krok5 color_correction_pct : {d.get('krok5_color_correction_pct')}")
print(f"  krok5 color_netto          : {d.get('krok5_color_netto')}")
print(f"  krok5 body_netto           : {d.get('krok5_body_netto')}")
print(f"  krok6 vintage_pct          : {d.get('krok6_vintage_pct')}")
print(f"  krok6 final_rv_netto       : {d.get('krok6_final_rv_netto')}")
print(f"  krok6 wr_pct               : {d.get('krok6_wr_pct')}")

print("\n=== TRACE (human-readable) ===")
for step in rv_res["trace"]:
    print(f"  - {step['krok']}")
    print(f"      {step['rownanie']}")
    print(f"      => {step['wynik']:.2f}")

# 6) verdict
ok_net = abs(wr_net - EXPECTED_WR_NET) < 1.0
ok_pct = abs(wr_pct - EXPECTED_WR_PCT) < 0.001
print("\n=== VERDICT ===")
print(f"  WR net   match (|delta| < 1.00 PLN): {ok_net}")
print(f"  WR pct   match (|delta| < 0.1 pp )  : {ok_pct}")
print(f"  OVERALL                             : {'PASS' if ok_net and ok_pct else 'FAIL'}")
