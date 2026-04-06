import asyncio
from api.schemas.calculator import CalculatorInput
from core.database import supabase
from core.LTRKalkulator import LTRKalkulator


async def debug_pipeline():
    res = (
        supabase.table("ltr_kalkulacje")
        .select("stan_json")
        .eq("numer_kalkulacji", "KALK/2026/03/F3AD10")
        .execute()
    )
    if not res.data:
        print("Calc not found!")
        return

    stan = res.data[0]["stan_json"]
    print("STAN JSON KEYS:")
    print("keys:", list(stan.keys()))
    print("cena_podstawowa_brutto:", stan.get("cena_podstawowa_brutto"))
    print("base_price_net:", stan.get("base_price_net"))
    try:
        calc_input = CalculatorInput(**stan)
        # Mocking the missing field until the new DB records generate it
        calc_input.paint_type_name = stan.get("typ_lakieru") or "Metalik"
    except Exception as e:
        print("Model parse error:", e)
        return

    try:
        from core.models import ControlCenterSettings

        settings_res = (
            supabase.table("control_center").select("*").eq("id", 1).execute()
        )
        settings = ControlCenterSettings(**settings_res.data[0])
    except Exception as e:
        print("Settings fetch error:", e)
        return

    calc = LTRKalkulator(input_data=calc_input, settings=settings)
    # Give it a base price and parse other attributes from calc_input
    calc.vehicle.price_net = stan.get("base_price_net", 0.0)
    calc._apply_explicit_input_overrides()

    print("DEBUG VEHICLE:")
    print(f"paint_type_name (raw): {getattr(calc_input, 'paint_type_name', None)}")
    print(f"is_metalic: {getattr(calc.vehicle, 'is_metalic', None)}")
    print(f"paint_type_id: {getattr(calc.vehicle, 'paint_type_id', None)}")
    print(f"body_type_id: {getattr(calc.vehicle, 'body_type_id', None)}")

    try:
        matrix = calc.build_matrix()
        if not matrix:
            print("Matrix empty!")
            return

        c0 = matrix[0]
        print("Keys in cell:", c0.keys() if isinstance(c0, dict) else dir(c0))
        for c in matrix:
            okres = c.get("Okres", c.get("months"))
            przebieg = c.get("Przebieg", c.get("km_per_year"))
            if okres == 48 and przebieg == 35000:
                print("==========================================")
                print("CELL 48/35k (140k total):")
                print(f"CenaZakupu: {c.get('CenaZakupu')}")
                print(f"WR: {c.get('WR')}")
                traces = c.get("calculation_trace", [])
                for t in traces:
                    if "WR" in str(t):
                        print(f"TRACE: {t}")
                        print(f"TRACE: {t}")
                print("==========================================")

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_pipeline())
