import os
import json
from supabase import create_client, Client

ONLINE_URL = "https://gnpsdiarmwvqhqbyetce.supabase.co"
ONLINE_KEY = "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"

client = create_client(ONLINE_URL, ONLINE_KEY)


def main():
    print("Fetching Skoda Superb from online DB...")
    # Search for Superb
    resp = (
        client.table("vehicle_synthesis")
        .select("*")
        .ilike("model", "%Superb%")
        .execute()
    )

    if not resp.data:
        print("No Superb found in vehicle_synthesis. Trying dealer_pricing_requests...")
        # Since we might not have the ID, let's fetch any Skoda
        dpr_resp = (
            client.table("dealer_pricing_requests")
            .select("*")
            .ilike("request_data->>offer_number", "%120331%")
            .execute()
        )

        if dpr_resp.data:
            print(f"Found request: {dpr_resp.data[0]['id']}")
            vid = dpr_resp.data[0]["vehicle_id"]
            resp = client.table("vehicle_synthesis").select("*").eq("id", vid).execute()
        else:
            print("Offer not found in dealer_pricing_requests.")

    if resp.data:
        print(f"Found {len(resp.data)} Superbs. Saving to superb_data.json")
        with open("superb_data.json", "w", encoding="utf-8") as f:
            json.dump(resp.data, f, ensure_ascii=False, indent=2)

        print("Superb vehicle IDs:", [r["id"] for r in resp.data])

        # Also let's try to get feature evidence and state for this vehicle to see what online DB has.
        vid = resp.data[0]["id"]
        ev = (
            client.table("vehicle_feature_evidence")
            .select("*")
            .eq("source_vehicle_id", vid)
            .execute()
        )
        with open("superb_evidence.json", "w", encoding="utf-8") as f:
            json.dump(ev.data, f, ensure_ascii=False, indent=2)
        print(f"Found {len(ev.data)} evidence records online.")
    else:
        print("Failed to find the vehicle.")


if __name__ == "__main__":
    main()
