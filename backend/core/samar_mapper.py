"""Dynamic SAMAR class mapper using KlasaSAMAR_czak dictionary + Gemini Flash."""

import json
import os
from typing import Tuple

from google import genai
from google.genai import types
from supabase import Client, create_client


def _build_samar_client() -> Client:
    """Create a lightweight Supabase client for SAMAR lookups."""
    url = os.environ.get("VITE_SUPABASE_URL", "")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY", "")
    return create_client(url, key)


def _fetch_samar_dictionary(client: Client) -> list[dict]:
    """Fetch SAMAR class dictionary rows from ``KlasaSAMAR_czak``.

    Returns a list of dicts: ``[{"klasa": "PODSTAWOWA D ŚREDNIA", "modele": "1. Alfa Romeo ..."}]``
    """
    response = (
        client.table("KlasaSAMAR_czak")
        .select("col_1, col_8, col_9")
        .order("col_9")
        .execute()
    )
    rows: list[dict] = []
    for row in response.data:
        klasa = (row.get("col_1") or "").strip()
        modele = (row.get("col_8") or "").strip()
        if klasa and modele:
            rows.append({"klasa": klasa, "modele": modele})
    return rows


def _build_gemini_client() -> genai.Client:
    """Create a Gemini client (API key or Vertex AI)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project, location=location)


def map_to_samar_class(
    brand: str,
    model: str,
    segment: str | None = None,
    body_style: str | None = None,
    trim: str | None = None,
    transmission: str | None = None,
) -> Tuple[str, str]:
    """Dynamically classify a vehicle into an official SAMAR class.

    Queries ``KlasaSAMAR_czak`` for the full dictionary, then asks
    Gemini Flash to pick the single best match.

    Returns
    -------
    tuple[str, str]
        ``(short_code, full_class_name)`` e.g. ``("D", "PODSTAWOWA D ŚREDNIA")``.
        Falls back to ``("UNKNOWN", "INNE - WYMAGA RĘCZNEGO MAPOWANIA")`` on error.
    """
    fallback = ("UNKNOWN", "INNE - WYMAGA RĘCZNEGO MAPOWANIA")

    if not brand and not model:
        return fallback

    try:
        sb_client = _build_samar_client()
        samar_dict = _fetch_samar_dictionary(sb_client)
    except Exception:
        return fallback

    if not samar_dict:
        return fallback

    # Build a compact representation for the prompt
    dict_text = "\n".join(
        f"- {row['klasa']}: {row['modele'][:200]}" for row in samar_dict
    )

    prompt = f"""Jesteś ekspertem klasyfikacji pojazdów wg macierzy IBRM SAMAR 2025.

Oto PEŁNY słownik klas SAMAR wraz z przykładowymi modelami przypisanymi do każdej klasy:
{dict_text}

Pojazd do klasyfikacji:
- Marka: {brand}
- Model: {model}
- Wersja/Trim: {trim or "brak danych"}
- Skrzynia biegów: {transmission or "brak danych"}
- Typ nadwozia: {body_style or "brak danych"}
- Segment: {segment or "brak danych"}

ZADANIE: Przypisz ten pojazd do DOKŁADNIE JEDNEJ klasy z powyższego słownika.
Szukaj marki i modelu w listach przykładowych modeli. Zwróć SZCZEGÓLNĄ uwagę na typ nadwozia oraz wersję. 
Na przykład, ten sam wiodący model (jak 'VW Crafter' lub 'Ford Transit') może występować jako auto dostawcze ("S. DOSTAWCZE I CIĘŻAROWE..." lub "DOSTAWCZE") 
w wariancie 'Furgon' / ciężarowym, albo jako auto osobowe/bus ("MINIBUS I MINIBUS" lub "VANY...") w wariancie 'Osobowy' / 'Tourneo'.
Zawsze wybieraj najbardziej adekwatną klasę biorąc pod uwagę czy to osobówka, czy auto użytkowe/cargo.
"""

    try:
        gemini = _build_gemini_client()
        response = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "klasa": {
                            "type": "string",
                            "description": "Dokładna nazwa klasy SAMAR ze słownika, np. 'PODSTAWOWA D ŚREDNIA'.",
                        },
                    },
                    "required": ["klasa"],
                },
            ),
        )

        resp_text = getattr(response, "text", "{}") or "{}"
        result = json.loads(resp_text)
        matched_class = result.get("klasa", "").strip()

        if matched_class:
            # Derive a short code from the class name
            code = _extract_short_code(matched_class)
            return (code, matched_class)

    except Exception as exc:
        print(f"[SAMAR MAPPER] Gemini error: {exc}")

    return fallback


def _extract_short_code(class_name: str) -> str:
    """Extract a short segment code like 'D' or 'Csuv' from a full SAMAR class name.

    Examples
    --------
    >>> _extract_short_code("PODSTAWOWA D ŚREDNIA")
    'D'
    >>> _extract_short_code("TERENOWO-REKREACYJNE C NIŻSZA ŚREDNIA")
    'Csuv'
    >>> _extract_short_code("VANY C MINIVANY")
    'Cvan'
    """
    name_lower = class_name.lower()

    # Detect category prefix
    is_suv = "terenowo" in name_lower
    is_sport = "sportowo" in name_lower
    is_van = "vany" in name_lower or "minivan" in name_lower or "kombi" in name_lower
    is_dostawcze = "dostawcze" in name_lower
    is_minibus = "minibus" in name_lower
    is_pickup = "pick-up" in name_lower

    # Detect segment letter
    segment = ""
    for letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]:
        if f" {letter} " in class_name:
            segment = letter
            break

    if not segment:
        if "luksus" in name_lower:
            segment = "F"
        elif "mini" in name_lower and not is_minibus:
            segment = "A"

    # Build compound code
    if is_suv:
        return f"{segment}suv"
    if is_sport:
        return f"{segment}sport"
    if is_van:
        return f"{segment}van"
    if is_dostawcze:
        return "DOSTx"
    if is_minibus:
        return "MINIBUS"
    if is_pickup:
        return "PICKUP"

    return segment or "UNKNOWN"
