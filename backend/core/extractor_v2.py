import json
from typing import Union

from core.pipeline_digital_twin import extract_digital_twin_from_pdf
from core.pipeline_card_summary import generate_card_summary_from_twin
from core.pipeline_discounts import match_fleet_discount
from core.pipeline_overrides import process_manual_override


def extract_vehicle_data_v2(
    document_data: Union[str, bytes], mime_type: str = "application/pdf"
) -> str:
    """
    Orchestrates the modular extraction pipeline:
    1. Extracts Digital Twin (Gemini 2.5 Pro)
    2. Generates Card Summary & Classifies Doc Type (Gemini 2.5 Flash)
    3. Matches Fleet Discounts from DB (Gemini 2.5 Flash)
    """
    try:
        # 1. Digital Twin extraction
        pro_data = extract_digital_twin_from_pdf(document_data, mime_type)
        if not pro_data:
            return "{}"

        # 2. Card Summary classification and mapping
        pro_data = generate_card_summary_from_twin(pro_data)

        # 3. Apply Fleet Discount Matching
        pro_data = match_fleet_discount(pro_data)

        return json.dumps(pro_data, ensure_ascii=False)

    except Exception as e:
        print(f"Error in modular extractor pipeline: {e}")
        return "{}"


def process_manual_override_v2(original_json: dict, user_prompt: str) -> str:
    """
    Delegates user override patching to the pipeline_overrides module.
    """
    try:
        return process_manual_override(original_json, user_prompt)
    except Exception as e:
        print(f"Error in manual override pipeline: {e}")
        return json.dumps(original_json, ensure_ascii=False)
