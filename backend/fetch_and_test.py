import json
import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.background_jobs import get_supabase_client
from google import genai
from google.genai import types
from core.json_utils import clean_json_response
from core.extractor_models import CardSummary
from core.prompts import CARD_SUMMARY_PROMPT


def re_run_pro_fallback():
    supabase = get_supabase_client()

    # Fetch latest 10 vehicles
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, synthesis_data, created_at")
        .order("created_at", desc=True)
        .limit(4)
        .execute()
    )

    for row in res.data:
        syn = row.get("synthesis_data") or {}
        card_summary = syn.get("card_summary") or {}
        base_price = card_summary.get("base_price", "")
        options_price = card_summary.get("options_price", "")
        power = card_summary.get("powertrain", "")

        print(f"Checking: {row['brand']} {row['model']} (ID: {row['id']})")
        print(f"  base_price: {base_price}")
        print(f"  options_price: {options_price}")
        print(f"  powertrain: {power}")

        print(f"\n--- Running PRO FALLBACK on Vehicle {row['id']} ---")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("NO API KEY!")
            return
        client = genai.Client(api_key=api_key)
        pro_model_id = "gemini-2.5-pro"

        pro_response_text = json.dumps(syn, ensure_ascii=False)

        flash_config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=CardSummary,
            system_instruction=CARD_SUMMARY_PROMPT,
        )

        try:
            model_res = client.models.generate_content(
                model=pro_model_id,
                contents=[types.Part.from_text(text=pro_response_text)],
                config=flash_config,
            )

            flash_json_str = getattr(model_res, "text", "{}") or "{}"
            flash_data = json.loads(clean_json_response(str(flash_json_str)))

            print(f"PRO FALLBACK Result for base_price: {flash_data.get('base_price')}")
            print(
                f"PRO FALLBACK Result for options_price: {flash_data.get('options_price')}"
            )
            print(f"PRO FALLBACK Result for powertrain: {flash_data.get('powertrain')}")
            print("-" * 50)
        except Exception as e:
            print(f"Error calling PRO: {e}")


if __name__ == "__main__":
    re_run_pro_fallback()
