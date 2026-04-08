import os
import sys

# Add backend to path so we can import core components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.database import supabase as sb_client


def main():
    vehicle_id = (
        "0b0800ed-ccbb-46f9-bd4d-ac67ff2d3921"  # A random vehicle from previous tests
    )

    # Let's just fetch 1 row from the view to see the keys
    resp = (
        sb_client.schema("reverse_search")
        .table("vehicle_features_summary_view")
        .select("*")
        .limit(1)
        .execute()
    )

    if resp.data:
        print("vehicle_features_summary_view columns:")
        print(resp.data[0].keys())
        print("Sample data:", resp.data[0])
    else:
        print("No data found in view.")


if __name__ == "__main__":
    main()
