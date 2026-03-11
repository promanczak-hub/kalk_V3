import os

# Configure to use local supabase
os.environ["SUPABASE_URL"] = "http://127.0.0.1:54321"
os.environ["SUPABASE_KEY"] = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlZmF1bHQiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTY4MjUwMDUxNiwiZXhwIjoxOTk4MDc2NTE2fQ.yS5yZ7B12bX0sXyC_kQ62S7bKkRz74pA_fT2o1w"
)

from core.database import supabase


def main():
    print("Checking vehicle_synthesis...")
    resp = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, version, synthesis_data")
        .ilike("model", "%Superb%")
        .execute()
    )
    data = resp.data
    print(f"Found {len(data)} Superb vehicles.")

    for row in data:
        vid = row["id"]
        brand = row["brand"]
        model = row["model"]
        version = row["version"]

        synth = row.get("synthesis_data") or {}
        card = synth.get("card_summary") or {}
        std = card.get("standard_equipment") or []
        paid = card.get("paid_options") or []

        print(f"Vehicle: {vid} | {brand} {model} {version}")
        print(f"  Standard Equipment count: {len(std)}")
        if len(std) > 0:
            print(f"    Sample: {std[:3]}")
        print(f"  Paid Options count: {len(paid)}")
        if len(paid) > 0:
            print(f"    Sample: {paid[:3]}")


if __name__ == "__main__":
    main()
