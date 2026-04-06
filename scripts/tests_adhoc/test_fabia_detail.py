from core.database import supabase
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input


def main():
    fabia_id = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"
    print(f"Testowowanie Fabii w detailach: {fabia_id}")

    res = supabase.table("vehicle_synthesis").select("*").eq("id", fabia_id).execute()
    if not res.data:
        print("Brak pojazdu w tabeli vehicle_synthesis!")
        return

    vehicle = res.data[0]

    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    if not settings_res.data:
        print("Brak settings!")
        return
    settings = ControlCenterSettings(**settings_res.data[0])

    calc_input = build_calculator_input(vehicle, 0.0, settings)
    if not calc_input:
        print(
            "build_calculator_input zwrocil None! SamochĂłd zostanie zignorowany przez refresh_matrix_cache_for_vehicles."
        )
    else:
        print(f"Calc Input OK: base_price_net={calc_input.base_price_net}")


if __name__ == "__main__":
    main()
