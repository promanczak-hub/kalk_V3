import os
from dotenv import load_dotenv

load_dotenv(".env")
from supabase import create_client, ClientOptions

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
s = create_client(
    url, key, ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60)
)

res = (
    s.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB. PRZEBIEG")
    .limit(1)
    .execute()
)
przebieg_rows = res.data[0].get("data_rows", [])

res2 = (
    s.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB.WR KLASA")
    .limit(1)
    .execute()
)
wr_rows = res2.data[0].get("data_rows", [])

import unicodedata


def normalize_key(k: str) -> str:
    s = k.lower().strip()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("utf-8")
    return s.replace(" ", "").replace("-", "").replace("_", "")


p_keys = [normalize_key(r.get("col_1", "")) for r in przebieg_rows]
w_keys = [normalize_key(r.get("col_1", "")) for r in wr_rows]

print("P KEYS[:5]:", p_keys[:5])
print("W KEYS[:5]:", w_keys[:5])

matches = set(p_keys).intersection(set(w_keys))
print(f"Intersection len: {len(matches)}")

print("\nExample P:", p_keys[5] if p_keys else None)
print("Example W:", w_keys[5] if w_keys else None)
