from core.database import supabase
from core.matrix_cache_job import build_calculator_input
from core.models import ControlCenterSettings
from core.LTRKalkulator import LTRKalkulator

cc = supabase.table("control_center").select("*").eq("id", 1).execute().data[0]
settings = ControlCenterSettings(**cc)
print(f"Settings wibor: {settings.default_wibor}, margin: {settings.bank_spread}")

vehicles = (
    supabase.table("vehicle_synthesis")
    .select("*")
    .in_("offer_number", ["CYJT98P6", "CSVZ5HMV"])
    .execute()
    .data
)
for v in vehicles:
    print(f"\n--- {v['brand']} {v['model']} ({v['offer_number']}) ---")
    inp = build_calculator_input(v, margin_pct=0.0, settings=settings)
    if not inp:
        print("No calc input!")
        continue
    print(f"Base Price Net: {inp.base_price_net}")
    fact_opts = sum(o.price_net for o in inp.factory_options)
    print(f"Factory Opts Net: {fact_opts}")
    print(f"Total Price Net: {inp.base_price_net + fact_opts}")

    calc = LTRKalkulator(input_data=inp, settings=settings)
    cells = calc.build_matrix()
    cell = next((c for c in cells if c["Okres"] == 48 and c["Przebieg"] == 30000), None)
    if cell:
        print(f"LacznaStawka (raw cache value, 0% margin): {cell['LacznaStawka']}")

    calc2 = LTRKalkulator(input_data=inp, settings=settings)
    calc2.input_data.pricing_margin_pct = 20.0
    cells2 = calc2.build_matrix()
    cell2 = next(
        (c for c in cells2 if c["Okres"] == 48 and c["Przebieg"] == 30000), None
    )
    if cell2:
        print(
            f"LacznaStawka (with 20% margin inside calculator): {cell2['LacznaStawka']}"
        )
