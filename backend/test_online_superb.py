import os
import json
from supabase import create_client, Client

ONLINE_URL = "https://gnpsdiarmwvqhqbyetce.supabase.co"
ONLINE_KEY = "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"

client = create_client(ONLINE_URL, ONLINE_KEY)


def main():
    print("Querying online database for Superb...")
    resp = (
        client.table("vehicle_synthesis")
        .select("id, brand, model, version, synthesis_data")
        .ilike("model", "%Superb%")
        .execute()
    )

    print(f"Found {len(resp.data)} Superb records")
    for row in resp.data:
        vid = row["id"]
        synth = row.get("synthesis_data") or {}
        card = synth.get("card_summary") or {}
        std_eq = card.get("standard_equipment") or []
        paid_opt = card.get("paid_options") or []

        print(f"--- {row['brand']} {row['model']} {row['version']} ({vid}) ---")
        print(f"Std Eq items: {len(std_eq)}")
        if len(std_eq) > 0:
            print(f"Sample Std Eq: {std_eq[:3]}")

        print(f"Paid Opt items: {len(paid_opt)}")
        if len(paid_opt) > 0:
            print(f"Sample Paid Opt: {[o.get('name') for o in paid_opt[:3]]}")

        # Check raw equipment if present
        raw_eq = synth.get("raw_equipment") or {}
        if raw_eq:
            print(f"Raw equipment keys: {list(raw_eq.keys())}")

        print()


if __name__ == "__main__":
    main()
