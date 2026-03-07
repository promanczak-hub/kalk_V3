import json
from typing import Union
from google.genai import types

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
from core.json_utils import clean_json_response
from core.prompts import (
    MASTER_PROMPT_V2,
    FALLBACK_STRUCTURED_PROMPT_FLASH,
    TWIN_RERANKING_PROMPT,
)


from pydantic import BaseModel
from typing import List, Optional


class EquipmentItem(BaseModel):
    name: str
    price: Optional[str] = None


class FlatVehicleExtractionSchema(BaseModel):
    brand: str
    model: str
    offer_number: Optional[str] = None
    configuration_code: Optional[str] = None
    total_price: Optional[str] = None
    base_price: Optional[str] = None
    options_price: Optional[str] = None
    engine_power_hp: Optional[str] = None
    engine_capacity_cm3: Optional[str] = None
    fuel_consumption: Optional[str] = None
    co2_emissions: Optional[str] = None
    transmission: Optional[str] = None
    drive_type: Optional[str] = None
    paint_color: Optional[str] = None
    wheels: Optional[str] = None
    upholstery: Optional[str] = None
    standard_equipment: List[str]
    optional_equipment: List[EquipmentItem]


def _call_gemini_pro(client, contents) -> dict:
    model_id = "gemini-2.5-pro"
    config = types.GenerateContentConfig(
        temperature=0.0,
        seed=42,
        max_output_tokens=65536,
        response_mime_type="application/json",
        system_instruction=MASTER_PROMPT_V2,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        thinking_config=types.ThinkingConfig(
            thinking_budget=16384,
        ),
    )
    print("Attempting primary standard JSON extraction with Pro (thinking enabled)...")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=config,
        )
        pro_response_text = getattr(response, "text", "{}") or "{}"

        usage = getattr(response, "usage_metadata", None)
        usage_info: dict = {}
        if usage:
            usage_info = {
                "prompt_tokens": getattr(usage, "prompt_token_count", None),
                "output_tokens": getattr(usage, "candidates_token_count", None),
                "thinking_tokens": getattr(usage, "thoughts_token_count", None),
                "model": model_id,
                "stage": "digital_twin",
            }
            print(
                f"[GEMINI USAGE] prompt={usage_info['prompt_tokens']}, "
                f"output={usage_info['output_tokens']}, "
                f"thinking={usage_info['thinking_tokens']}"
            )

        pro_data = json.loads(clean_json_response(pro_response_text))
        if usage_info:
            pro_data["_extraction_metadata"] = usage_info
        print("Pro standard JSON extraction succeeded.")
        return pro_data
    except Exception as e:
        print(f"Extraction failed with JSONDecodeError or other error (Pro): {e}")
        return {}


def _call_gemini_flash(client, contents) -> dict:
    fallback_model_id = "gemini-2.5-flash"
    fallback_config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=FlatVehicleExtractionSchema,
        system_instruction=FALLBACK_STRUCTURED_PROMPT_FLASH,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )
    print("Attempting parallel structured extraction with Flash...")
    try:
        fallback_response = client.models.generate_content(
            model=fallback_model_id,
            contents=contents,
            config=fallback_config,
        )
        fallback_text = getattr(fallback_response, "text", "{}") or "{}"
        fallback_data = json.loads(clean_json_response(fallback_text))

        unified_data = {
            "brand": fallback_data.get("brand", ""),
            "model": fallback_data.get("model", ""),
            "offer_number": fallback_data.get("offer_number", ""),
            "configuration_code": fallback_data.get("configuration_code", ""),
            "digital_twin": {
                "pricing": {
                    "total_price": fallback_data.get("total_price"),
                    "base_price": fallback_data.get("base_price"),
                    "options_price": fallback_data.get("options_price"),
                },
                "technical": {
                    "power": fallback_data.get("engine_power_hp"),
                    "capacity": fallback_data.get("engine_capacity_cm3"),
                    "fuel_consumption": fallback_data.get("fuel_consumption"),
                    "co2": fallback_data.get("co2_emissions"),
                    "transmission": fallback_data.get("transmission"),
                    "drive": fallback_data.get("drive_type"),
                },
                "features": {
                    "color": fallback_data.get("paint_color"),
                    "wheels": fallback_data.get("wheels"),
                    "upholstery": fallback_data.get("upholstery"),
                },
                "standard_equipment": fallback_data.get("standard_equipment", []),
                "optional_equipment": fallback_data.get("optional_equipment", []),
            },
        }

        usage = getattr(fallback_response, "usage_metadata", None)
        if usage:
            unified_data["_extraction_metadata"] = {
                "prompt_tokens": getattr(usage, "prompt_token_count", None),
                "output_tokens": getattr(usage, "candidates_token_count", None),
                "thinking_tokens": getattr(usage, "thoughts_token_count", None),
                "model": fallback_model_id,
                "stage": "digital_twin_flash",
            }
        print("Flash Structured Output extraction succeeded.")
        return unified_data
    except Exception as fallback_e:
        print(f"Flash extraction completely failed: {fallback_e}")
        return {}


def evaluate_and_rank_twins(client, twin_a: dict, twin_b: dict) -> dict:
    """
    Uses an LLM (gemini-2.5-flash) to evaluate which digital twin is better extracted.
    Twin A is from Pro, Twin B is from Flash.
    """
    print("Starting LLM-as-a-judge reranking...")
    twin_a_str = json.dumps(twin_a, ensure_ascii=False)
    twin_b_str = json.dumps(twin_b, ensure_ascii=False)

    prompt = f"Oto wariant A (wygenerowany przez model A):\n{twin_a_str}\n\nOto wariant B (wygenerowany przez model B):\n{twin_b_str}"

    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        system_instruction=TWIN_RERANKING_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Part.from_text(text=prompt)],
            config=config,
        )
        response_text = getattr(response, "text", "{}") or "{}"
        evaluation = json.loads(clean_json_response(response_text))

        best_candidate = evaluation.get("best_candidate", "A")
        reasoning = evaluation.get("reasoning", "Brak uzasadnienia")

        print(f"Reranking result: Wygrał {best_candidate}. Powód: {reasoning}")

        if best_candidate == "B":
            print("Returning Twin B (Flash fallback version).")
            twin_b["_evaluation_reasoning"] = reasoning
            return twin_b
        else:
            print("Returning Twin A (Pro version).")
            twin_a["_evaluation_reasoning"] = reasoning
            return twin_a

    except Exception as e:
        print(f"Reranking failed: {e}. Defaulting to Twin A (Pro).")
        return twin_a


def extract_digital_twin_from_pdf(
    document_data: Union[str, bytes], mime_type: str = "application/pdf"
) -> dict:
    """
    Extracts a raw JSON digital twin representation of the document using Gemini 2.5 Pro and Gemini 2.5 Flash in parallel.
    Uses LLM-as-a-judge to select the best output (preventing bad price splits).
    """
    client = get_gemini_client()

    if isinstance(document_data, bytes):
        contents: list[types.Part] = [
            types.Part.from_bytes(data=document_data, mime_type=mime_type),
        ]
    else:
        contents = [types.Part.from_text(text=document_data)]

    import concurrent.futures

    twin_pro = {}
    twin_flash = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_pro = executor.submit(_call_gemini_pro, client, contents)
        future_flash = executor.submit(_call_gemini_flash, client, contents)

        twin_pro = future_pro.result()
        twin_flash = future_flash.result()

    if not twin_pro and twin_flash:
        print("Pro failed completely, returning Flash result.")
        return twin_flash
    elif not twin_flash and twin_pro:
        print("Flash failed completely, returning Pro result.")
        return twin_pro
    elif not twin_pro and not twin_flash:
        print("Both extractions failed entirely.")
        return {}

    return evaluate_and_rank_twins(client, twin_pro, twin_flash)
