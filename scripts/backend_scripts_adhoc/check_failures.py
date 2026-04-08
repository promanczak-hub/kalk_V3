import logging
import traceback
from core.database import supabase
from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput

logging.basicConfig(level=logging.ERROR)


def check_vehicle(config_code):
    out = [f"\n--- Sprawdzanie {config_code} ---"]
    try:
        res = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
        vid = None
        for r in res.data:
            if config_code in str(r):
                vid = r["id"]
                break

        if not vid:
            out.append(f"Nie znaleziono pojazdu z kodem {config_code}")
            return "\\n".join(out)

        out.append(f"Znaleziono vehicle_id: {vid}")

        # Get all kalkulacje and find the one for this vehicle_id
        res_kalk = supabase.table("ltr_kalkulacje").select("id, stan_json").execute()
        stan_json = None
        for k in res_kalk.data:
            sj = k.get("stan_json") or {}
            if str(sj.get("vehicle_id")) == str(vid):
                stan_json = sj
                break

        if not stan_json:
            out.append(f"Nie znaleziono ltr_kalkulacje dla pojazdu {vid}")
            return "\\n".join(out)

        try:
            calc_input = CalculatorInput(**stan_json)
        except Exception as e:
            out.append(f"Błąd parsera Pydantic: {e}")
            out.append(traceback.format_exc())
            return "\\n".join(out)

        settings_res = (
            supabase.table("control_center").select("*").eq("id", 1).execute()
        )
        from core.models import ControlCenterSettings

        settings = ControlCenterSettings(**settings_res.data[0])

        try:
            engine = LTRKalkulator(input_data=calc_input, settings=settings)
            engine.build_matrix()
            out.append("Kalkulacja przebiegła POMYŚLNIE!")
        except Exception:
            out.append("ZNKALEZIONO BŁĄD PODCZAS KALKULACJI:")
            out.append(traceback.format_exc())

    except Exception as general_e:
        out.append(f"General error: {general_e}")
        out.append(traceback.format_exc())

    return "\\n".join(out)


res1 = check_vehicle("CBGM55VH")
res2 = check_vehicle("CBQDKGWL")

with open("d:/kalk_v3/backend/cbgm_trace.txt", "w", encoding="utf-8") as f:
    f.write(res1 + "\\n" + res2)
