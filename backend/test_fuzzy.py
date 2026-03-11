import json
from supabase import create_client

ONLINE_URL = "https://gnpsdiarmwvqhqbyetce.supabase.co"
ONLINE_KEY = "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"

client = create_client(ONLINE_URL, ONLINE_KEY)

# Import the matching logic
from core.feature_enrichment import (
    _build_feature_index,
    _fuzzy_match,
)


def main():
    # Load catalog from online DB
    features_resp = (
        client.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key, display_name, feature_type")
        .execute()
    )
    aliases_resp = (
        client.schema("reverse_search")
        .table("universal_feature_aliases")
        .select("feature_id, alias_text, normalized_alias")
        .execute()
    )

    features = features_resp.data or []
    aliases = aliases_resp.data or []

    print(
        f"Loaded {len(features)} universal features and {len(aliases)} aliases from online DB."
    )

    feature_index = _build_feature_index(features, aliases)

    # Load the Superb data
    with open("superb_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)[0]

    synth = data.get("synthesis_data", {})
    card = synth.get("card_summary", {})
    std_eq = card.get("standard_equipment", [])

    matched_count = 0
    # Test fuzzy match
    print("\n--- Standard Equipment Matches ---")
    for item in std_eq:
        feat_id = _fuzzy_match(item, feature_index)
        if feat_id:
            # Find the feature name
            feat_name = next(
                (f["display_name"] for f in features if f["id"] == feat_id), "Unknown"
            )
            print(f"[MATCH] '{item}' -> {feat_name}")
            matched_count += 1
        else:
            print(f"[NO MATCH] '{item}'")

    print(f"\nTotal matched: {matched_count} out of {len(std_eq)}")


if __name__ == "__main__":
    main()
