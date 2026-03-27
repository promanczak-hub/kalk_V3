import json
import traceback

from dotenv import load_dotenv

load_dotenv(".env")

from core.database import supabase
from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput
from core.models import ControlCenterSettings


def main():
    try:
        resp = (
            supabase.table("ltr_kalkulacje")
            .select("*")
            .eq("id", "84f2185b-2ca7-4181-8e20-57f077dc0ca0")
            .execute()
        )
        db_calc = resp.data[0]
        stan_json = db_calc["stan_json"]
        calc_input = CalculatorInput(**stan_json)

        cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        cc_settings = ControlCenterSettings(**cc_res.data[0])

        kalk = LTRKalkulator(input_data=calc_input, settings=cc_settings)
        res = kalk.build_matrix()

        target = None
        for r in res:
            if r.get("Okres") == 48 and r.get("PrzebiegKontrakt") == 140000:
                target = r
                break

        with open("matrix_output.json", "w", encoding="utf-8") as f:
            json.dump(target or {"error": "Not found in matrix"}, f, indent=2)

        print("Successfully wrote matrix_output.json")
    except Exception:
        with open("trace.txt", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)


if __name__ == "__main__":
    main()
