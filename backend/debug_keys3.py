import os
import json
from dotenv import load_dotenv

load_dotenv(".env")
from supabase import create_client, ClientOptions
import unicodedata

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
s = create_client(
    url, key, ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60)
)

przebieg_rows = (
    s.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB. PRZEBIEG")
    .limit(1)
    .execute()
    .data[0]
    .get("data_rows", [])
)
wr_rows = (
    s.table("excel_drafts")
    .select("data_rows")
    .eq("sheet_name", "TAB.WR KLASA")
    .limit(1)
    .execute()
    .data[0]
    .get("data_rows", [])
)


def normalize_key(k: str) -> str:
    s = str(k).lower().strip()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("utf-8")
    return s.replace(" ", "").replace("-", "").replace("_", "")


p_keys = [
    normalize_key(r.get("col_1", ""))
    for r in przebieg_rows
    if str(r.get("col_1")) != "nan"
]
w_keys = [
    normalize_key(r.get("col_1", "")) for r in wr_rows if str(r.get("col_1")) != "nan"
]

out = {
    "P_KEYS_5": p_keys[:5],
    "W_KEYS_5": w_keys[:5],
    "MATCHES": list(set(p_keys).intersection(w_keys)),
}
with open("dump_keys.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
