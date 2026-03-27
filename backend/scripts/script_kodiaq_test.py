import json
from dotenv import load_dotenv

load_dotenv()

from core.database import supabase
from core.pipeline_card_summary import generate_card_summary_from_twin


def test_kodiaq():
    print("Fetching Kodiaq CXY6G6NG from database...")
    resp = (
        supabase.table("vehicle_synthesis")
        .select("synthesis_data")
        .eq("import_id", "CXY6G6NG")
        .execute()
    )
    if not resp.data:
        print("Kodiaq not found!")
        return

    digital_twin = resp.data[0].get("synthesis_data", {}).get("digital_twin", {})
    if not digital_twin:
        print("No digital twin in the DB for Kodiaq!")
        return

    # In pipeline, we pass document_text if we have it. For the test, digital_twin is sufficient.
    text = ""

    print("Executing LLM generation with Structured Outputs (gemini-2.5-pro)...")
    try:
        summary = generate_card_summary_from_twin(
            digital_twin, text, model_name="gemini-2.5-pro"
        )
        print("\n=== GENERATED CARD SUMMARY ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error generating summary: {e}")


if __name__ == "__main__":
    test_kodiaq()
