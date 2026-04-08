import json
import logging
from typing import Union
from google.genai import types

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
from core.json_utils import clean_json_response
from core.prompts import (
    MASTER_PROMPT_V2,
    FALLBACK_STRUCTURED_PROMPT_FLASH,
)


from pydantic import BaseModel, Field
from typing import List, Optional

logger = logging.getLogger(__name__)


from core.extractor_models import CargoAndDimensions


class EquipmentItem(BaseModel):
    name: str = Field(description="Nazwa wyposażenia rzetelnie odczytana z dokumentu")
    price: Optional[str] = Field(
        None, description="Cena wyposażenia, jeśli przypisana wprost"
    )


class VehicleExtractionSchema(BaseModel):
    brand: str = Field(
        description="Zidentyfikowana marka pojazdu, np. Volkswagen, Skoda, Audi"
    )
    model: str = Field(
        description="Zidentyfikowany główny model pojazdu (bez marki i bez wersji wyposażenia), np. Tayron, Kodiaq, A6"
    )
    trim_level: Optional[str] = Field(
        None, description="Wersja wyposażenia / linia, np. L&K, Elegance, R-Line"
    )
    offer_number: Optional[str] = Field(
        None, description="Numer oferty widoczny na dokumencie (jeśli występuje)"
    )
    configuration_code: Optional[str] = Field(
        None, description="Kod konfiguracji producenta (jeśli występuje)"
    )
    total_price: Optional[str] = Field(
        None, description="Pełna cena brutto/netto podana jako wynikowa"
    )
    base_price: Optional[str] = Field(
        None, description="Cena bazowa pojazdu wynikająca z cenników przed opcjami"
    )
    options_price: Optional[str] = Field(
        None, description="Cena wariantów/opcji dodatkowych"
    )
    engine_power_hp: Optional[str] = Field(None, description="Moc silnika (np. 150 KM)")
    engine_capacity_cm3: Optional[str] = Field(
        None, description="Pojemność silnika (np. 1498 cm3)"
    )
    fuel_consumption: Optional[str] = Field(None, description="Zużycie paliwa / WLTP")
    co2_emissions: Optional[str] = Field(None, description="Emisje CO2 w g/km")
    transmission: Optional[str] = Field(
        None, description="Rodzaj skrzyni biegów (np. Automatyczna DSG)"
    )
    drive_type: Optional[str] = Field(
        None, description="Typ napędu (np. 4x4, oś przednia)"
    )
    paint_color: Optional[str] = Field(
        None, description="Kolor zewnętrzny nadwozia (najlepiej z cennikiem obok)"
    )
    wheels: Optional[str] = Field(
        None, description="Szczegóły dotyczące kół/obręczy aluminiowych"
    )
    upholstery: Optional[str] = Field(
        None, description="Informacje o wyposażeniu tapicerki/wnętrza"
    )
    standard_equipment: List[str] = Field(
        description="Kompletne wylistowanie wyposażenia standardowego / seryjnego z dokumentu"
    )
    optional_equipment: List[EquipmentItem] = Field(
        description="Lista płatnego i darmowego wybranego wyposażenia (opcje/akcesoria/pakiety)"
    )
    dimensions: Optional[CargoAndDimensions] = Field(
        None,
        description="Wymiary, masy, pojemności i ładowność pojazdu - Bądź agresywny w szukaniu!",
    )


def _format_unified_data(extracted_data: dict) -> dict:
    return {
        "brand": extracted_data.get("brand", ""),
        "model": extracted_data.get("model", ""),
        "trim_level": extracted_data.get("trim_level", ""),
        "offer_number": extracted_data.get("offer_number", ""),
        "configuration_code": extracted_data.get("configuration_code", ""),
        "digital_twin": {
            "pricing": {
                "total_price": extracted_data.get("total_price"),
                "base_price": extracted_data.get("base_price"),
                "options_price": extracted_data.get("options_price"),
            },
            "technical": {
                "power": extracted_data.get("engine_power_hp"),
                "capacity": extracted_data.get("engine_capacity_cm3"),
                "fuel_consumption": extracted_data.get("fuel_consumption"),
                "co2": extracted_data.get("co2_emissions"),
                "transmission": extracted_data.get("transmission"),
                "drive": extracted_data.get("drive_type"),
            },
            "features": {
                "color": extracted_data.get("paint_color"),
                "wheels": extracted_data.get("wheels"),
                "upholstery": extracted_data.get("upholstery"),
            },
            "standard_equipment": extracted_data.get("standard_equipment", []),
            "optional_equipment": extracted_data.get("optional_equipment", []),
            "dimensions": extracted_data.get("dimensions"),
        },
    }


def _call_gemini_pro(client, contents) -> dict:
    model_id = "gemini-2.5-pro"
    config = types.GenerateContentConfig(
        temperature=0.0,
        seed=42,
        max_output_tokens=65536,
        response_mime_type="application/json",
        response_schema=VehicleExtractionSchema,
        system_instruction=MASTER_PROMPT_V2,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        thinking_config=types.ThinkingConfig(
            thinking_budget=16384,
        ),
    )
    print(
        "Attempting primary standard JSON extraction with Pro (Thinking + Structured Outputs)..."
    )
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
                "stage": "digital_twin_pro_structured",
            }
            print(
                f"[GEMINI USAGE] prompt={usage_info['prompt_tokens']}, "
                f"output={usage_info['output_tokens']}, "
                f"thinking={usage_info['thinking_tokens']}"
            )

        pro_data_raw = json.loads(clean_json_response(pro_response_text))
        unified_data = _format_unified_data(pro_data_raw)

        if usage_info:
            unified_data["_extraction_metadata"] = usage_info
        print("Pro standard JSON extraction succeeded.")
        return unified_data
    except Exception as e:
        logger.exception(
            f"Extraction failed with JSONDecodeError or other error (Pro): {e}"
        )
        return {}


def _call_gemini_flash(client, contents) -> dict:
    fallback_model_id = "gemini-2.5-flash"
    fallback_config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=VehicleExtractionSchema,
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

        unified_data = _format_unified_data(fallback_data)

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
        logger.exception(f"Flash extraction completely failed: {fallback_e}")
        return {}


def extract_digital_twin_from_pdf(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
    text_data: Optional[str] = None,
) -> dict:
    """
    Extracts a raw JSON digital twin representation of the document using Gemini 2.5 Pro.
    Falls back to Gemini 2.5 Flash if Pro fails completely.
    """
    client = get_gemini_client()

    contents: list[types.Part] = []

    if text_data:
        contents.append(
            types.Part.from_text(
                text=f"--- EXTRACTED TEXT (MARKDOWN) ---\n{text_data}\n--- END EXTRACTED TEXT ---\n\nThe original document is attached below. Use BOTH the markdown text and the visual document to extract all features, dimensions, weights, and packages. Pay special attention to visual diagrams with measurements."
            )
        )

    if isinstance(document_data, bytes):
        contents.append(types.Part.from_bytes(data=document_data, mime_type=mime_type))
    else:
        contents.append(types.Part.from_text(text=document_data))

    twin_pro = _call_gemini_pro(client, contents)

    if twin_pro:
        return twin_pro

    print("[DIGITAL TWIN] Pro failed — falling back to Flash.")
    twin_flash = _call_gemini_flash(client, contents)

    if twin_flash:
        return twin_flash

    print("[DIGITAL TWIN] Both Pro and Flash failed entirely.")
    return {}
