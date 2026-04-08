import sys
import os

sys.path.append(os.path.abspath("."))
from core.database import supabase

keys = [
    "instalacja_lpg_taknie",
    "marka_instalacji_lpg",
    "zasięg_wltp_dla_pojazdów_elektrycznych_w_km",
    "pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh",
    "funkcja_szybkiego_ładowania_samochodu",
]

result = (
    supabase.schema("reverse_search")
    .table("universal_features")
    .select("technical_key, powertrain_context")
    .in_("technical_key", keys)
    .execute()
)
print("Weryfikacja DB (powertrain_context):")
for row in result.data:
    print(f"  {row['technical_key']}: {row['powertrain_context']}")
