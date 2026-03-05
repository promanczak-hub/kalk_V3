"""Fix all stuck vehicle records (any in-progress status)."""

import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv("../frontend/.env.local")

STUCK_STATUSES = [
    "processing",
    "uploading",
    "detecting_vehicles",
    "extracting_twin",
    "generating_summary",
    "matching_discounts",
    "mapping_data",
]


def fix_all_stuck() -> None:
    url = os.environ["VITE_SUPABASE_URL"]
    key = os.environ["VITE_SUPABASE_ANON_KEY"]
    supabase = create_client(url, key)

    # First, list stuck records
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, verification_status, brand, model")
        .in_("verification_status", STUCK_STATUSES)
        .execute()
    )

    if not res.data:
        print("Brak zablokowanych rekordów.")
        return

    print(f"Znaleziono {len(res.data)} zablokowanych rekordów:")
    for row in res.data:
        vid = row["id"][:8]
        status = row["verification_status"]
        brand = row.get("brand") or "?"
        model = row.get("model") or "?"
        print(f"  {vid}... | {status} | {brand} {model}")

    # Reset all stuck records to 'error'
    for status in STUCK_STATUSES:
        supabase.table("vehicle_synthesis").update(
            {
                "verification_status": "error",
                "notes": f"Zresetowano ze statusu '{status}' — backend nie był uruchomiony.",
            }
        ).eq("verification_status", status).execute()

    print(f"\nZresetowano {len(res.data)} rekordów do statusu 'error'.")


if __name__ == "__main__":
    fix_all_stuck()
