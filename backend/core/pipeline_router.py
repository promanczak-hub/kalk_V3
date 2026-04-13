import json
import logging
from typing import Union, Dict, Any, Tuple
from google.genai import types

from core.gemini_client import (
    get_gemini_client,
    SAFETY_SETTINGS_PERMISSIVE,
    generate_content_with_retry,
)
from core.json_utils import clean_json_response

logger = logging.getLogger(__name__)

# Typy dokumentów do rozpoznania przez router
DOC_TYPE_OFFER = "OFFER"
DOC_TYPE_PRICE_LIST = "PRICE_LIST"
DOC_TYPE_BROCHURE = "BROCHURE"
DOC_TYPE_OTHER = "OTHER"

ROUTER_SYSTEM_PROMPT = """
Jesteś inteligentnym routerem dokumentów motoryzacyjnych. Otrzymujesz na wejściu pełen tekst dokumentu (skonwertowany na format Markdown m.in. z PDF).
Twoim głównym zadaniem jest głęboka analiza treści oraz bezbłędna klasyfikacja otrzymanego dokumentu do jednej z 4 kategorii:
- OFFER (Oferta, zamówienie, konfiguracja biznesowa, SPECYFIKACJA dla konkretnego klienta na konkretny egzemplarz lub egzemplarze, często zawierająca zniżki i dane leasingowe). Należą tu również pliki opisujące wybrane wyposażenie pojazdu, np. "Crafter L3H3 spec1". Nawet jeśli to zestawienie wielu aut w Excelu (Multi-Vehicle) - jeżeli każde ma swoją cenę i status przygotowanej de facto oferty, to jest to OFFER.
- PRICE_LIST (Cennik ogólny modelu, zawierający wiele wierszy z wersjami silnikowymi/wyposażenia bez wskazania na zakup konkretnego auta).
- BROCHURE (Broszura reklamowa, katalog opisujący technologie i wygląd pojazdu).
- OTHER (Pozostałe dokumenty, np. wyciągi z homologacji, dowody rejestracyjne, noty prawne. UWAGA: specyfikacje dealerskie to OFFER, nie OTHER!).

KRYTYCZNE ZADANIE:
Na podstawie zawartości zidentyfikuj typ. Jeśli to nie jest oferta (czyli jest to PRICE_LIST, BROCHURE lub OTHER), musisz również wyciągnąć podstawowe metadane (brand, model, date, description), które posłużą do zapisania dokumentu w Bibliotece Cenników. Jeśli to OFFER, metadane mogą pozostać puste (zajmie się nimi dedykowany pipeline Ofert).

Zwróć wynik jako CZYSTY obiekt JSON z następującymi kluczami:
{
  "document_type": "OFFER" | "PRICE_LIST" | "BROCHURE" | "OTHER",
  "metadata": {
    "brand": "np. Skoda (lub null jeśli brak/OFFER)",
    "model": "np. Superb (lub null jeśli brak/OFFER)",
    "date": "np. 2024-05-10 (data ważności/publikacji lub null)",
    "description": "Krótkie, 1-2 zdaniowe podsumowanie zawartości dokumentu (tylko dla PRICE_LIST/BROCHURE/OTHER)."
  }
}
Odpowiedz WYŁĄCZNIE używając składni JSON.
"""


def _build_document_parts(
    document_data: Union[str, bytes], mime_type: str
) -> list[types.Part]:
    if isinstance(document_data, bytes):
        return [types.Part.from_bytes(data=document_data, mime_type=mime_type)]
    return [types.Part.from_text(text=document_data)]


def classify_document(
    document_data: Union[str, bytes], mime_type: str = "application/pdf"
) -> Tuple[str, Dict[str, Any]]:
    """
    Analizuje dokument za pomocą Gemini Flash w celu ustalenia jego typu biznesowego.
    Zwraca krotkę: (document_type, metadata_dict)
    """
    client = get_gemini_client()
    contents = _build_document_parts(document_data, mime_type)

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        system_instruction=ROUTER_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        thinking_config=types.ThinkingConfig(
            thinking_budget=4096,
        ),
    )

    try:
        logger.info("[ROUTER] Analyzing document with Gemini Pro to determine type...")
        response = generate_content_with_retry(
            client=client,
            model="gemini-2.5-pro",
            contents=contents,
            config=config,
        )

        raw_text = getattr(response, "text", "{}") or "{}"
        data = json.loads(clean_json_response(raw_text))

        doc_type = data.get("document_type", DOC_TYPE_OTHER)
        # Fallback security if AI hallucinates type
        if doc_type not in [
            DOC_TYPE_OFFER,
            DOC_TYPE_PRICE_LIST,
            DOC_TYPE_BROCHURE,
            DOC_TYPE_OTHER,
        ]:
            doc_type = DOC_TYPE_OTHER

        metadata = data.get("metadata", {})

        logger.info(f"[ROUTER] Document classified as: {doc_type}")
        return doc_type, metadata

    except json.JSONDecodeError as e:
        logger.warning(f"[ROUTER] JSON decode error from Flash: {e}")
        return DOC_TYPE_OTHER, {}
    except Exception as e:
        logger.warning(f"[ROUTER] Classification error: {e}")
        return DOC_TYPE_OTHER, {}
