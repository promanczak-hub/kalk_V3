import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))

from core.database import supabase
from core.LTRKalkulator import LTRKalkulator
from core.models import ControlCenterSettings
from api.schemas.calculator import CalculatorInput


class MockSettings:
    default_wibor = 5.85
    normatywny_przebieg_mc = 1667
    ins_avg_damage_value = 1.0
    ins_doubezp_zarobkowe_procent = 1.15


settings = MockSettings()


def main():
    # Fetch CC Settings from DB (just like matrix_cache_job)
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings_dict = settings_res.data[0]
    settings = ControlCenterSettings(**settings_dict)

    # Let's get the UUID first because Kalkulator needs the actual UUID!
    vid = None
    res = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
    syn_data = {}
    for r in res.data:
        if "CBQDKGWL" in str(r.get("synthesis_data", "")):
            vid = r["id"]
            syn_data = r["synthesis_data"]
            break

    import json

    if not vid:
        print("Vehicle not found!")
        return

    print("RAW SYNTHESIS SD:")
    print(json.dumps(syn_data.get("card_summary", {}), indent=2))

    # 1. Provide the exact inputs that the Extractor would send
    calc_input = CalculatorInput(
        vehicle_id=vid,
        base_price_net=124500.0,  # TO DO: We will see the real one from print
        discount_pct=27.0,
        margin_pct=2.0,  # bank spread
        wibor_pct=5.85,  # Default WIBOR
        z_oponami=True,
        srednica_felgi=18,
        klasa_opony_string="Medium",
        pricing_margin_pct=14.0,  # 14% markup!
        okres_bazowy=36,
        przebieg_bazowy=150000,
        service_cost_type="ASO",
        matrix_km_mode="annual",
    )

    try:
        # 2. Run Kalkulator
        kalk = LTRKalkulator(calc_input, settings)
        matrix = kalk.build_matrix()

        if matrix:
            for cell in matrix:
                if cell["okres_mc"] == 36 and cell["przebieg_roczny"] == 50000:
                    print("\nFOUND MATRIX CELL (36m, 50k annual / 150k total)")
                    print(f"Stawka (Oferowana): {cell['oferowana_stawka']}")
                    print(
                        json.dumps(
                            cell["calculation_trace"], indent=2, ensure_ascii=False
                        )
                    )
        else:
            print("Matrix build failed!")

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
