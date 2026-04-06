import os
import sys
from dotenv import load_dotenv

load_dotenv()
from supabase import create_client


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Missing SUPABASE environment variables.")
        sys.exit(1)

    sb = create_client(url, key)
    code = "CPYJZ25F"
    print(f"Searching for vehicle with code {code}...")

    # Try different paths in JSONB
    res = sb.table("vehicle_synthesis").select("id, synthesis_data").execute()

    found = []
    for row in res.data:
        sd = row.get("synthesis_data", {})
        if not sd:
            continue

        # Check metadata in digital_twin or card_summary
        dt_code = (
            sd.get("digital_twin", {}).get("metadata", {}).get("configuration_code")
        )
        cs_code = (
            sd.get("card_summary", {}).get("metadata", {}).get("configuration_code")
        )

        if dt_code == code or cs_code == code:
            found.append(row["id"])
            print(f"Found match: {row['id']}")

    if not found:
        print("No match found.")
    else:
        print(f"Total found IDs: {found}")


if __name__ == "__main__":
    main()
