import traceback
from core.database import supabase
from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput

kalk_id = "8390ff7f-4a9e-4ce0-aaf1-8284649ac733"
res = supabase.table("ltr_kalkulacje").select("*").eq("id", kalk_id).execute()
stan_json = res.data[0].get("stan_json", {})

calc_input = CalculatorInput(**stan_json)

settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
from core.models import ControlCenterSettings

settings = ControlCenterSettings(**settings_res.data[0])

try:
    engine = LTRKalkulator(input_data=calc_input, settings=settings)
    engine.build_matrix()
except Exception:
    traceback.print_exc()
