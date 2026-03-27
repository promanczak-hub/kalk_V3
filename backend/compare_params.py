"""Run identical LTRKalkulator with two CalculatorInputs and compare prices.

Path A: build_calculator_input (reverse search)
Path B: CalculatorInput(**stan_json) from ltr_kalkulacje (Vertex)
"""

import logging

logging.basicConfig(level=logging.WARNING)
from core.matrix_cache_job import build_calculator_input
from core.database import supabase
from core.models import ControlCenterSettings
from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput

BMW_ID = "749333ec-06be-4913-be43-fb7895f559bb"

# Load shared resources
v = supabase.table("vehicle_synthesis").select("*").eq("id", BMW_ID).execute()
s = supabase.table("control_center").select("*").eq("id", 1).execute()
settings = ControlCenterSettings(**s.data[0])
vehicle = v.data[0]

# ── PATH A: Reverse Search (build_calculator_input) ──
ci_rev = build_calculator_input(vehicle, margin_pct=15.0, settings=settings)
ci_rev.okres_bazowy = 48
ci_rev.przebieg_bazowy = 150000

engine_rev = LTRKalkulator(input_data=ci_rev, settings=settings)
cells_rev = engine_rev.build_matrix(only_exact=True)
rev_price = None
for c in cells_rev:
    if c.get("Okres") == 48:
        rev_price = c.get("LacznaStawka")
        rev_cell = c
        break

print(f"=== PATH A (Reverse Search): {rev_price} PLN ===")

# ── PATH B: Vertex (stan_json) ──
kalk = (
    supabase.table("ltr_kalkulacje")
    .select("stan_json")
    .eq("id", "806c325c-bcba-433b-bcc3-3d3b30e4390e")
    .execute()
)
stan = kalk.data[0]["stan_json"]

try:
    ci_vtx = CalculatorInput(**stan)
    # Force same mileage/duration as path A
    ci_vtx.okres_bazowy = 48
    ci_vtx.przebieg_bazowy = 150000

    engine_vtx = LTRKalkulator(input_data=ci_vtx, settings=settings)
    cells_vtx = engine_vtx.build_matrix(only_exact=True)
    vtx_price = None
    for c in cells_vtx:
        if c.get("Okres") == 48:
            vtx_price = c.get("LacznaStawka")
            vtx_cell = c
            break

    print(f"=== PATH B (Vertex stan_json): {vtx_price} PLN ===")
    print(f"\nDELTA: {abs((rev_price or 0) - (vtx_price or 0)):.0f} PLN")

    # Compare key fields
    print("\n=== KEY FIELD COMPARISON ===")
    for field in [
        "base_price_net",
        "discount_pct",
        "pricing_margin_pct",
        "margin_pct",
        "samar_category",
        "engine_name",
        "samar_class_id",
        "engine_id",
        "body_type_id",
        "z_oponami",
        "klasa_opony_string",
        "pakiet_serwisowy",
        "service_cost_type",
        "replacement_car_enabled",
        "transport_koszt_netto",
        "gsm_koszt_netto",
    ]:
        val_a = getattr(ci_rev, field, "N/A")
        val_b = getattr(ci_vtx, field, "N/A")
        marker = " <<< DIFF" if str(val_a) != str(val_b) else ""
        print(f"  {field:30s}: rev={val_a!s:>20s} | vtx={val_b!s:>20s}{marker}")

    # Compare cost components
    if rev_price and vtx_price and rev_price != vtx_price:
        print("\n=== COST COMPONENT COMPARISON ===")
        for key in [
            "CzynszFinansowy",
            "Serwis",
            "Opony",
            "Ubezpieczenie",
            "SamochodZastepczy",
            "Admin",
            "CenaZakupu",
            "WR",
        ]:
            va = rev_cell.get(key) if rev_cell else None
            vb = vtx_cell.get(key) if vtx_cell else None
            marker = " <<< DIFF" if va != vb else ""
            print(f"  {key:25s}: rev={va!s:>12s} | vtx={vb!s:>12s}{marker}")

except Exception as e:
    print(f"ERROR parsing stan_json: {e}")
    import traceback

    traceback.print_exc()
