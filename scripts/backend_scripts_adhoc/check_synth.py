import json
import traceback
from core.database import supabase
from core.extractor_v2 import process_single_twin


def test_reprocess():
    with open("check_output.txt", "w", encoding="utf-8") as f:
        try:
            synth_id = "011fd704-5f53-4813-afd2-fc53ff9d2cdb"  # Cupra Terramar
            f.write(f"Fetching {synth_id}\n")
            resp = (
                supabase.table("vehicle_synthesis")
                .select("synthesis_data")
                .eq("id", synth_id)
                .execute()
            )
            data = resp.data[0]["synthesis_data"]

            f.write(
                "Original utility_features: "
                + json.dumps(data.get("card_summary", {}).get("utility_features"))
                + "\n"
            )

            f.write("Reprocessing...\n")
            # We must use suppress or handle stdout if it's polluting, but we are writing to file anyway
            new_json_str = process_single_twin(data)
            new_data = json.loads(new_json_str)
            cs = new_data.get("card_summary", {})
            f.write(
                "New utility_features: " + json.dumps(cs.get("utility_features")) + "\n"
            )
            f.write("New card_summary keys: " + json.dumps(list(cs.keys())) + "\n")
        except Exception:
            f.write(traceback.format_exc())


if __name__ == "__main__":
    test_reprocess()
