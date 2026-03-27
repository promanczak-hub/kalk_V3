from core.database import supabase
from core.matrix_cache_job import build_calculator_input
from core.models import ControlCenterSettings

res = (
    supabase.table("vehicle_synthesis")
    .select("*")
    .eq("id", "4efad866-2b72-4dca-a5bd-dc7f857c1443")
    .execute()
)
row = res.data[0]
res2 = supabase.table("control_center").select("*").eq("id", 1).execute()
settings = ControlCenterSettings(**res2.data[0])
calc_input = build_calculator_input(row, margin_pct=0.0, settings=settings)
print("BASE PRICE NET:", calc_input.base_price_net)
print("DISCOUNT:", calc_input.discount_pct)
