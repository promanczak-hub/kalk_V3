import json
from dotenv import load_dotenv

load_dotenv()

from core.database import supabase
from core.extractor_v2 import process_single_twin
from core.feature_enrichment import enrich_vehicle_features


def main():
    print("Fetching all vehicle_synthesis records...")
    response = (
        supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
    )

    records = response.data
    print(f"Found {len(records)} records. Reprocessing...")

    for record in records:
        synth_id = record["id"]
        data = record.get("synthesis_data", {})

        if not data or "digital_twin" not in data:
            print(f"Skipping {synth_id} - no digital_twin found.")
            continue

        print(f"Reprocessing {synth_id} to recover utility features...")
        try:
            # Reprocess to regenerate card summary with utility features included
            new_json_str = process_single_twin(data)
            new_data = json.loads(new_json_str)

            # Update supabase
            supabase.table("vehicle_synthesis").update({"synthesis_data": new_data}).eq(
                "id", synth_id
            ).execute()

            # Re-run feature enrichment so the newly extracted utility features map to vehicle_features
            enrich_vehicle_features(synth_id, new_data)
            print(f"Successfully reprocessed {synth_id}")
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Error reprocessing {synth_id}: {e}")

    print("All done!")


if __name__ == "__main__":
    main()
