import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(r"d:\kalk_v3\backend\.env")

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Remove quotes from the key if they exist
if key.startswith('"') and key.endswith('"'):
    key = key[1:-1]
if url.startswith('"') and url.endswith('"'):
    url = url[1:-1]

supabase: Client = create_client(url, key)

res = (
    supabase.table("samar_class_depreciation_rates")
    .update({"options_depreciation_percent": 0.26})
    .eq("samar_class_id", 103)
    .eq("fuel_type_id", 2)
    .eq("year", 4)
    .execute()
)

print("UPDATED DATA:", res.data)
