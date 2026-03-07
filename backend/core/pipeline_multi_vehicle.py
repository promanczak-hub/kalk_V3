"""
Phase 0: Multi-vehicle detection and splitting.

Uses Gemini Flash to determine if a document contains multiple
vehicles. If so, uses Gemini Pro to extract N separate digital twins.
If only 1 vehicle, returns early and lets the standard pipeline handle it.
"""

import json
import logging
from typing import Union

from google.genai import types

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
from core.json_utils import clean_json_response
from core.prompts import MULTI_VEHICLE_DETECTION_PROMPT

logger = logging.getLogger(__name__)

# Polish word-to-number mapping for Flash responses
_WORD_TO_NUM: dict[str, int] = {
    "jeden": 1,
    "dwa": 2,
    "trzy": 3,
    "cztery": 4,
    "pięć": 5,
    "sześć": 6,
    "siedem": 7,
    "osiem": 8,
    "dziewięć": 9,
    "dziesięć": 10,
}


def _build_document_parts(
    document_data: Union[str, bytes],
    mime_type: str,
) -> list[types.Part]:
    """Convert raw document bytes/text into Gemini-compatible parts."""
    if isinstance(document_data, bytes):
        return [types.Part.from_bytes(data=document_data, mime_type=mime_type)]
    return [types.Part.from_text(text=document_data)]


def detect_vehicle_count(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
) -> int:
    """
    Lightweight Phase-0 probe using Gemini Flash.

    Returns the number of separate vehicle offers detected in the document.
    Falls back to 1 on any error.
    """
    client = get_gemini_client()
    doc_parts = _build_document_parts(document_data, mime_type)

    detection_prompt = types.Part.from_text(
        text=(
            "\n\n---\n"
            "INSTRUKCJA: Powyżej znajduje się zawartość dokumentu (oferta na pojazdy).\n"
            "Policz ile RÓŻNYCH pojazdów (różnych modeli/konfiguracji) "
            "jest opisanych w tym dokumencie.\n\n"
            "ZASADY LICZENIA:\n"
            "- Każdy ODRĘBNY model pojazdu = 1 osobny pojazd.\n"
            "- Różne modele od TEGO SAMEGO producenta to OSOBNE pojazdy! "
            "Przykład: Lexus ES + Lexus RX + Lexus NX = 3 pojazdy.\n"
            "- Różne marki w jednym dokumencie = osobne pojazdy. "
            "Przykład: Toyota Corolla + Lexus NX = 2 pojazdy.\n"
            "- W arkuszu Excel (XLSX) każdy arkusz/zakładka z osobnym pojazdem "
            "= 1 pojazd (arkusz 'Podsumowanie'/'Summary' NIE jest osobnym pojazdem).\n"
            "- W pliku PDF szukaj osobnych sekcji cenowych, osobnych tabel specyfikacji, "
            "osobnych kodów konfiguracji lub osobnych numerów ofert — "
            "każda taka sekcja = 1 pojazd.\n"
            "- WYJĄTEK: Jeśli jest JEDEN cennik z wieloma wersjami silnikowymi "
            "JEDNEGO modelu (np. Skoda Octavia 1.0 TSI / 1.5 TSI / 2.0 TDI) "
            "= 1 pojazd (cennik ogólny).\n\n"
            "PRZYKŁADY:\n"
            "- PDF z ofertą na Lexus ES 300h, Lexus RX 450h i Lexus NX 350h → 3\n"
            "- PDF z ofertą na Renault Trafic, Kangoo Van, Master → 3\n"
            "- XLSX z 9 arkuszami, każdy z innym Renault → 9\n"
            "- PDF cennik Skoda Octavia z 4 wersjami silnika → 1\n"
            "- PDF z Toyota Yaris + Lexus UX → 2\n\n"
            "ODPOWIEDZ WYŁĄCZNIE jedną liczbą całkowitą. "
            "Nic więcej, żadnych wyjaśnień.\n"
            "ODPOWIEDŹ:"
        )
    )

    # Send document + prompt together as contents
    contents = doc_parts + [detection_prompt]

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=16,
        response_mime_type="text/plain",
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )
        raw_text = (getattr(response, "text", "1") or "1").strip()
        logger.info("[MULTI-VEHICLE] Raw Flash response: '%s'", raw_text)
        # Extract first number if Flash adds extra text
        digits = (
            "".join(c for c in raw_text.split()[0] if c.isdigit()) if raw_text else "1"
        )
        if digits:
            count = int(digits)
        else:
            # Fallback: try Polish word-to-number
            first_word = raw_text.split()[0].lower() if raw_text else ""
            count = _WORD_TO_NUM.get(first_word, 1)
            if count > 1:
                logger.info(
                    "[MULTI-VEHICLE] Parsed word '%s' as %d",
                    first_word,
                    count,
                )
        logger.info("[MULTI-VEHICLE] Gemini Flash detected %d vehicle(s)", count)
        return max(count, 1)
    except (ValueError, TypeError) as e:
        logger.warning(
            "[MULTI-VEHICLE] Could not parse vehicle count, defaulting to 1: %s", e
        )
        return 1
    except Exception as e:
        logger.warning("[MULTI-VEHICLE] Detection error, defaulting to 1: %s", e)
        return 1


def extract_multi_vehicle_twins(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
    expected_count: int = 2,
) -> list[dict]:
    """
    Full multi-vehicle extraction using Gemini Pro.

    Sends the document with `MULTI_VEHICLE_DETECTION_PROMPT`
    which instructs Gemini to return N separate digital twins.

    Returns a list of dicts, each containing:
      - brand, model, offer_number, configuration_code, digital_twin
    """
    client = get_gemini_client()
    contents = _build_document_parts(document_data, mime_type)

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=65536,
        response_mime_type="application/json",
        system_instruction=MULTI_VEHICLE_DETECTION_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        thinking_config=types.ThinkingConfig(
            thinking_budget=16384,
        ),
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=contents,
            config=config,
        )
        raw_text = getattr(response, "text", "{}") or "{}"
        data = json.loads(clean_json_response(raw_text))

        vehicles = data.get("vehicles", [])
        if not isinstance(vehicles, list) or len(vehicles) == 0:
            logger.warning(
                "[MULTI-VEHICLE] Pro returned no vehicles array, falling back"
            )
            return []

        logger.info(
            "[MULTI-VEHICLE] Gemini Pro extracted %d vehicle twin(s)", len(vehicles)
        )
        return vehicles

    except json.JSONDecodeError as e:
        logger.warning("[MULTI-VEHICLE] JSON decode error from Pro: %s", e)
        return []
    except Exception as e:
        logger.warning("[MULTI-VEHICLE] Extraction error: %s", e)
        return []


def detect_and_split_vehicles(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
) -> list[dict] | None:
    """
    Main entry point for Phase 0.

    Returns:
      - None if document has exactly 1 vehicle (caller should use standard pipeline)
      - list[dict] with N vehicle dicts if N > 1
    """
    count = detect_vehicle_count(document_data, mime_type)

    if count <= 1:
        return None

    logger.info(
        "[MULTI-VEHICLE] Flash detected %d vehicles, sending to Pro for extraction...",
        count,
    )
    vehicles = extract_multi_vehicle_twins(
        document_data, mime_type, expected_count=count
    )

    if len(vehicles) < 2:
        # Retry once — Pro sometimes needs a stronger hint
        logger.info(
            "[MULTI-VEHICLE] Pro returned %d twin(s) (expected %d), retrying...",
            len(vehicles),
            count,
        )
        vehicles = extract_multi_vehicle_twins(
            document_data, mime_type, expected_count=count
        )

    if len(vehicles) < 2:
        logger.warning(
            "[MULTI-VEHICLE] Pro could not extract multiple twins "
            "after retry (got %d), fallback to single",
            len(vehicles),
        )
        return None

    if len(vehicles) != count:
        logger.warning(
            "[MULTI-VEHICLE] Count mismatch: Flash=%d vs Pro=%d",
            count,
            len(vehicles),
        )

    logger.info(
        "[MULTI-VEHICLE] Successfully extracted %d vehicles (Flash expected %d)",
        len(vehicles),
        count,
    )
    return vehicles
