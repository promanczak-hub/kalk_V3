import os
import sys
from dotenv import load_dotenv

load_dotenv(".env")

from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("No URL or KEY")
    sys.exit(1)

sb = create_client(url, key)

hanging_statuses = [
    "processing",
    "uploading",
    "classifying_document",
    "detecting_vehicles",
    "extracting_twin_1_of_2",
    "mapping_data",
    "enriching_features",
]

resp = (
    sb.table("vehicle_synthesis")
    .update(
        {
            "verification_status": "error",
            "notes": "Przerwano z powodu aktualizacji systemu - zwiśnięty proces po restarcie silnika.",
        }
    )
    .in_("verification_status", hanging_statuses)
    .execute()
)

print(f"Zaktualizowano {len(resp.data)} zawieszonych rekordów na 'error'.")
