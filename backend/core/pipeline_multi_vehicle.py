"""
Phase 0: Multi-vehicle detection and splitting.

Uses Gemini Flash to determine if a document contains multiple
vehicles. If so, uses Gemini Pro to extract N separate digital twins.
If only 1 vehicle, returns early and lets the standard pipeline handle it.
"""

import json
import os
from typing import Union

from google import genai
from google.genai import types

from core.json_utils import clean_json_response
from core.prompts import MULTI_VEHICLE_DETECTION_PROMPT


def _build_gemini_client() -> genai.Client:
    """Create Gemini client from env (API key or Vertex AI)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project_id, location=location)


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
    client = _build_gemini_client()
    doc_parts = _build_document_parts(document_data, mime_type)

    detection_prompt = types.Part.from_text(
        text=(
            "\n\n---\n"
            "INSTRUKCJA: Powyżej znajduje się zawartość dokumentu (oferta na pojazdy).\n"
            "Policz ile RÓŻNYCH pojazdów (różnych modeli/konfiguracji) "
            "jest opisanych w tym dokumencie.\n\n"
            "ZASADY LICZENIA:\n"
            "- Każdy ODRĘBNY model pojazdu = 1 pojazd "
            "(np. TRAFIC COMBI, KANGOO VAN, SYMBIOZ to 3 pojazdy)\n"
            "- W arkuszu Excel (XLSX) każdy arkusz/zakładka z osobnym pojazdem = 1 pojazd\n"
            "- Arkusz 'Podsumowanie' lub 'Summary' NIE jest osobnym pojazdem\n"
            "- Jeśli jest jeden cennik z wieloma wersjami silnikowymi JEDNEGO modelu = 1 pojazd\n"
            "- Różne marki/modele = różne pojazdy "
            "(np. Renault Austral + Dacia Duster = 2 pojazdy)\n\n"
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
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )
        raw_text = (getattr(response, "text", "1") or "1").strip()
        # Extract first number if Flash adds extra text
        digits = (
            "".join(c for c in raw_text.split()[0] if c.isdigit()) if raw_text else "1"
        )
        count = int(digits) if digits else 1
        print(f"[MULTI-VEHICLE] Gemini Flash detected {count} vehicle(s)")
        return max(count, 1)
    except (ValueError, TypeError) as e:
        print(f"[MULTI-VEHICLE] Could not parse vehicle count, defaulting to 1: {e}")
        return 1
    except Exception as e:
        print(f"[MULTI-VEHICLE] Detection error, defaulting to 1: {e}")
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
    client = _build_gemini_client()
    contents = _build_document_parts(document_data, mime_type)

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=65536,
        response_mime_type="application/json",
        system_instruction=MULTI_VEHICLE_DETECTION_PROMPT,
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
            print("[MULTI-VEHICLE] Pro returned no vehicles array, falling back")
            return []

        print(f"[MULTI-VEHICLE] Gemini Pro extracted {len(vehicles)} vehicle twin(s)")
        return vehicles

    except json.JSONDecodeError as e:
        print(f"[MULTI-VEHICLE] JSON decode error from Pro: {e}")
        return []
    except Exception as e:
        print(f"[MULTI-VEHICLE] Extraction error: {e}")
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

    vehicles = extract_multi_vehicle_twins(
        document_data, mime_type, expected_count=count
    )

    if len(vehicles) < 2:
        print(
            "[MULTI-VEHICLE] Pro could not extract multiple twins, fallback to single"
        )
        return None

    return vehicles
