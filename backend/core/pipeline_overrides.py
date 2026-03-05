import json
from google.genai import types

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE

from core.json_utils import clean_json_response
from core.extractor_models import (
    CardSummary,
    BrochureSummary,
    OtherDocumentSummary,
)
from core.prompts import OVERRIDE_SYSTEM_PROMPT


def process_manual_override(original_json: dict, user_prompt: str) -> str:
    """
    Function to process user-defined manual overrides on an existing extracted JSON.
    Uses Gemini 2.5 Flash to surgically patch the JSON without hallucinating or truncating data.
    """
    client = get_gemini_client()

    flash_model_id = "gemini-2.5-flash"

    # Determine type to select the right schema for the prompt
    metadata = original_json.get("digital_twin", {}).get("metadata", {})
    doc_type_str = metadata.get("document_type", "Oferta na samochód")

    from pydantic import BaseModel
    from typing import Type

    chosen_schema: Type[BaseModel]
    if doc_type_str == "Oferta na samochód":
        chosen_schema = CardSummary
    elif doc_type_str == "Cennik ogólny modelu":
        chosen_schema = BrochureSummary
    else:
        chosen_schema = OtherDocumentSummary

    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        response_schema=chosen_schema,
        system_instruction=OVERRIDE_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    card_summary_json = json.dumps(
        original_json.get("card_summary", {}), ensure_ascii=False
    )

    prompt = (
        f"Oryginalny JSON:\n{card_summary_json}\n\n"
        f"Instrukcja użytkownika (Modyfikacja Manualna):\n{user_prompt}"
    )

    response = client.models.generate_content(
        model=flash_model_id,
        contents=[types.Part.from_text(text=prompt)],
        config=config,
    )

    resp_text = getattr(response, "text", "{}") or "{}"
    new_card_summary = json.loads(clean_json_response(str(resp_text)))

    # Update original_json with patched data
    original_json["card_summary"] = new_card_summary
    return json.dumps(original_json, ensure_ascii=False)
