from core.database import supabase
from api.schemas.calculator import CalculatorInput
import pydantic

res = (
    supabase.table("ltr_kalkulacje")
    .select("id, stan_json")
    .eq("id", "087d6b7c-778c-4a92-b965-4b281eb90bda")
    .execute()
)
if res.data:
    stan_json = res.data[0].get("stan_json") or {}
    try:
        ci = CalculatorInput(**stan_json)
        print("SUCCESS:", ci.discount_pct)
    except pydantic.ValidationError as e:
        print("FAILED:")
        print(e)
