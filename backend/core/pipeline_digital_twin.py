import json
import logging
from typing import Union
from google.genai import errors as genai_errors
from google.genai import types

from core.gemini_client import (
    get_gemini_client,
    SAFETY_SETTINGS_PERMISSIVE,
    generate_content_with_retry,
    resolve_max_output_tokens,
)
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
    code: Optional[str] = Field(
        None, description="Kod opcji producenta jeśli widoczny (np. '9AK', '1D4', 'PWM')"
    )


class VehicleExtractionSchema(BaseModel):
    brand: str = Field(
        description=(
            "Zidentyfikowana marka pojazdu (TYLKO marka, bez modelu). "
            "Np. 'Volkswagen', 'Skoda', 'Audi', 'BMW'. "
            "BŁĘDNE: 'Volkswagen Tayron', 'Škoda Octavia'."
        )
    )
    model: str = Field(
        description=(
            "Główny model pojazdu — TYLKO nazwa modelu, BEZ marki, BEZ wersji wyposażenia, "
            "BEZ silnika, BEZ typu nadwozia, BEZ kodów rocznika. "
            "POPRAWNE: 'Tayron', 'Kodiaq', 'A6', 'Octavia', '320i', 'Santa Fe'. "
            "BŁĘDNE: "
            "'Octavia RS' (RS to trim), "
            "'Kodiaq Drive' (Drive to trim), "
            "'Octavia Combi' (Combi to body type), "
            "'A5 Avant' (Avant to body type → Kombi), "
            "'Audi A6' (Audi to brand), "
            "'320i xDrive Limuzyna' (xDrive to napęd, Limuzyna to body), "
            "'SUPERB RM2022 AMBITION' (RM2022 to year code, AMBITION to trim)."
        )
    )
    trim_level: Optional[str] = Field(
        None,
        description=(
            "Wersja wyposażenia / linia (TYLKO trim). "
            "Np. 'L&K', 'Elegance', 'R-Line', 'Sportline', 'Drive', 'Selection', 'RS', 'M Sport'. "
            "BŁĘDNE: '45 TFSI quattro' (to silnik+napęd), 'Furgon z wysokim dachem' (body), "
            "'Kombi N1' (body), '20 xDrive' (silnik). "
            "Jeśli klient nie ma jawnej wersji → null (NIE 'Brak', NIE pusty string)."
        ),
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
    summary_total_net: Optional[str] = Field(
        None,
        description=(
            "Cena KOŃCOWA NETTO z bloku PODSUMOWANIE / RAZEM / „do zapłaty”, ale TYLKO "
            "gdy dokument drukuje rozbicie netto / VAT / brutto. Sama jawna kwota netto "
            "sumy (np. '166 518,00'). null gdy brak takiego rozbicia."
        ),
    )
    summary_total_gross: Optional[str] = Field(
        None,
        description=(
            "Cena KOŃCOWA BRUTTO z tego samego bloku PODSUMOWANIE / RAZEM (np. "
            "'204 817,14'). Wypełnij PARĘ summary_total_net + summary_total_gross tylko "
            "gdy dokument podaje OBIE kwoty (netto i brutto) — inaczej obie null."
        ),
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
                # PODSUMOWANIE net/gross pair (when the doc prints netto/VAT/brutto) —
                # carried so deterministic normalize can set numeric total_price_net/gross
                # and the reconciliation engine gets an independent pair to catch flips.
                "total_net": extracted_data.get("summary_total_net"),
                "total_gross": extracted_data.get("summary_total_gross"),
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
        max_output_tokens=resolve_max_output_tokens(),
        response_mime_type="application/json",
        response_schema=VehicleExtractionSchema,
        system_instruction=MASTER_PROMPT_V2,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        thinking_config=types.ThinkingConfig(
            thinking_budget=16384,
        ),
    )
    logger.info(
        "Attempting primary standard JSON extraction with Pro (Thinking + Structured Outputs)..."
    )
    try:
        response = generate_content_with_retry(
            client=client,
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
            logger.info(
                "[GEMINI USAGE] prompt=%s, output=%s, thinking=%s",
                usage_info["prompt_tokens"],
                usage_info["output_tokens"],
                usage_info["thinking_tokens"],
            )

        pro_data_raw = json.loads(clean_json_response(pro_response_text))
        unified_data = _format_unified_data(pro_data_raw)

        if usage_info:
            unified_data["_extraction_metadata"] = usage_info
        logger.info("Pro standard JSON extraction succeeded.")
        return unified_data
    except genai_errors.ClientError as e:
        if getattr(e, "status", None) == "INVALID_ARGUMENT":
            logger.error(
                "[DIGITAL TWIN Pro] Gemini rejected response_schema "
                "(400 INVALID_ARGUMENT): %s. Flash uses the same schema, so "
                "neither retry nor model fallback recovers — re-raising so the "
                "vehicle record is marked 'error' instead of silently producing "
                "an empty digital twin.",
                e,
            )
            raise
        logger.exception(
            f"Extraction failed with client error other than INVALID_ARGUMENT (Pro): {e}"
        )
        return {}
    except Exception as e:
        logger.exception(
            f"Extraction failed with JSONDecodeError or other error (Pro): {e}"
        )
        return {}


def _call_gemini_flash(client, contents) -> dict:
    fallback_model_id = "gemini-2.5-flash"
    fallback_config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=resolve_max_output_tokens(),
        response_mime_type="application/json",
        response_schema=VehicleExtractionSchema,
        system_instruction=FALLBACK_STRUCTURED_PROMPT_FLASH,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )
    logger.info("Attempting parallel structured extraction with Flash...")
    try:
        fallback_response = generate_content_with_retry(
            client=client,
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
        logger.info("Flash Structured Output extraction succeeded.")
        return unified_data
    except genai_errors.ClientError as fallback_e:
        if getattr(fallback_e, "status", None) == "INVALID_ARGUMENT":
            logger.error(
                "[DIGITAL TWIN Flash] Gemini rejected response_schema "
                "(400 INVALID_ARGUMENT): %s. Same schema as Pro — recovery "
                "impossible without a code change. Re-raising so the vehicle "
                "record is marked 'error' instead of silently degrading.",
                fallback_e,
            )
            raise
        logger.exception(
            f"Flash extraction client error other than INVALID_ARGUMENT: {fallback_e}"
        )
        return {}
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

    twin = twin_pro
    if not twin:
        logger.warning("[DIGITAL TWIN] Pro failed — falling back to Flash.")
        twin = _call_gemini_flash(client, contents)

    if not twin:
        logger.error("[DIGITAL TWIN] Both Pro and Flash failed entirely.")
        return {}

    # Isolated, non-fatal extended-specs pass (tire labels, engine/towing/chassis
    # detail, offer metadata). Stored under digital_twin.extended_specs — purely
    # informational, never feeds the calculation. Failure here MUST NOT affect
    # the primary twin we already have.
    try:
        from core.pipeline_extended_specs import extract_extended_specs

        extended = extract_extended_specs(client, contents)
        if extended and isinstance(twin.get("digital_twin"), dict):
            twin["digital_twin"]["extended_specs"] = extended
    except Exception as e:  # noqa: BLE001 — isolation guarantee
        logger.warning("[DIGITAL TWIN] extended-specs pass skipped: %s", e)

    return twin
