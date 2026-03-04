"""
One-off script: Backfill missing card_summary fields from digital_twin
for all existing vehicle_synthesis records.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.pipeline_card_summary import _backfill_from_digital_twin

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
)


def main() -> None:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    response = (
        supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
    )
    records = response.data or []
    print(f"Znaleziono {len(records)} rekordów do sprawdzenia.")

    updated = 0
    for rec in records:
        sid = rec["id"]
        sd = rec.get("synthesis_data") or {}
        card_summary = sd.get("card_summary")
        digital_twin = sd.get("digital_twin")

        if not card_summary or not digital_twin:
            continue

        original = json.dumps(card_summary, sort_keys=True)
        patched = _backfill_from_digital_twin(
            json.loads(json.dumps(card_summary)),
            digital_twin,
        )
        if json.dumps(patched, sort_keys=True) != original:
            sd["card_summary"] = patched
            supabase.table("vehicle_synthesis").update({"synthesis_data": sd}).eq(
                "id", sid
            ).execute()
            updated += 1
            print(f"  ✓ Zaktualizowano: {sid}")

    print(f"\nGotowe. Zaktualizowano {updated}/{len(records)} rekordów.")


if __name__ == "__main__":
    main()
