from supabase import create_client

url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
key = "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"
vehicle_id = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"

sb = create_client(url, key)
try:
    # Based on list_tables verbose output, the column name is source_vehicle_id
    res = (
        sb.schema("reverse_search")
        .table("vehicle_feature_state")
        .select(
            "feature_id, resolved_value_num, reverse_search:universal_features(feature_key)"
        )
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )

    print(f"Features for vehicle {vehicle_id}:")
    found = False
    for r in res.data:
        val = r.get("resolved_value_num")
        if val is not None:
            feature_key = (
                r.get("reverse_search", {}).get("feature_key")
                if r.get("reverse_search")
                else None
            )
            # If join didn't work as expected, we might just see feature_id
            if not feature_key:
                # We'll just print what we have
                print(f"  Feature ID {r['feature_id']}: {val}")
                found = True
            else:
                relevant = [
                    "length_mm",
                    "width_mm",
                    "height_mm",
                    "wheelbase_mm",
                    "dmc_kg",
                    "curb_weight_kg",
                    "payload_kg",
                ]
                if feature_key in relevant:
                    print(f"  {feature_key}: {val}")
                    found = True
    if not found:
        print("  No numeric features (Dimensions/Masses) found.")
except Exception as e:
    print(f"Error: {e}")
