import traceback
from core.database import supabase
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input
from core.LTRKalkulator import LTRKalkulator


def main():
    fabia_id = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"
    print(f"Testowowanie Kalkulatora na Fabii: {fabia_id}")

    res = supabase.table("vehicle_synthesis").select("*").eq("id", fabia_id).execute()
    vehicle = res.data[0]

    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])

    calc_input = build_calculator_input(vehicle, 0.0, settings)
    print(f"Wejsie gotowe. Power_KW = {getattr(calc_input, 'power_kw', 'Brak')}")

    try:
        kalk = LTRKalkulator(calc_input, settings)
        print("Kalkulator zainicjowany. Test budowania matrixa.")
        cells = kalk.build_matrix()
        print(f"Zbudowano {len(cells)} komorek")
    except Exception as e:
        print(f"WYJATEK KALKULATORA: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
