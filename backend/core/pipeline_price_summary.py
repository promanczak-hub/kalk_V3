"""
Hybrid price summary generator.

Uses Gemini Flash to produce a natural-language summary of deterministic
price validation results.  Falls back to a template-based summary if
the LLM call fails.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google.genai import types

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE

logger = logging.getLogger(__name__)

_FLASH_MODEL = "gemini-2.5-flash"

_SYSTEM_PROMPT = (
    "Jesteś audytorem cenników flotowych. Dostajesz wynik walidacji "
    "deterministycznej (reguły arytmetyczne) dla cennika pojazdu.\n\n"
    "Na tej podstawie napisz krótkie podsumowanie (2-3 zdania) po polsku.\n"
    "Zwróć JSON:\n"
    '{"verdict": "<1 zdanie — główny wniosek>",'
    ' "confidence": "HIGH|MEDIUM|LOW",'
    ' "details": "<1-2 zdania wyjaśnienia>",'
    ' "suggestions": ["<konkretne kroki naprawcze>"]}\n\n'
    "Zasady:\n"
    "- HIGH = brak problemów, ceny spójne\n"
    "- MEDIUM = drobne ostrzeżenia (np. brak ceny opcji), ale baza OK\n"
    "- LOW = poważne błędy (swap pól, halucynacja sumy)\n"
    "- Jeśli wykryto BASE_TOTAL_SWAPPED, zasugeruj zamianę pól\n"
    "- Bądź zwięzły i konkretny, nie powtarzaj danych liczbowych\n"
)


def generate_price_summary(
    validation_dict: dict[str, Any],
    card_summary: dict[str, Any],
) -> dict[str, Any] | None:
    """Generate NL summary of price validation via Gemini Flash.

    Parameters
    ----------
    validation_dict:
        Output of ``ValidationReport.to_dict()`` — rules, warnings, parsed prices.
    card_summary:
        The card_summary dict (used for brand/model context).

    Returns
    -------
    dict with keys ``verdict``, ``confidence``, ``details``, ``suggestions``
    or ``None`` if generation fails and no warnings exist.
    """
    warnings = validation_dict.get("warnings", [])

    # Fast path: no warnings → deterministic HIGH without LLM call
    if not warnings:
        return _deterministic_high()

    # Build compact context for Flash
    context = _build_context(validation_dict, card_summary)

    try:
        return _call_flash(context)
    except Exception:
        logger.warning(
            "[PRICE SUMMARY] Gemini Flash failed — using deterministic fallback",
            exc_info=True,
        )
        return _deterministic_fallback(warnings)


def _deterministic_high() -> dict[str, Any]:
    """Return a static HIGH-confidence summary when all prices are valid."""
    return {
        "verdict": "Ceny spójne arytmetycznie",
        "confidence": "HIGH",
        "details": (
            "Baza + opcje = total. Wszystkie ceny w realistycznym zakresie. "
            "Brak wykrytych anomalii."
        ),
        "suggestions": [],
    }


def _deterministic_fallback(
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Template-based fallback when LLM is unavailable."""
    has_error = any(w.get("severity") == "ERROR" for w in warnings)
    rules = [w.get("rule", "") for w in warnings]

    if "BASE_TOTAL_SWAPPED" in rules:
        return {
            "verdict": "Prawdopodobna zamiana pól base↔total",
            "confidence": "LOW",
            "details": (
                "Cena bazowa jest wyższa od łącznej. "
                "Po zamianie pól arytmetyka się zgadza."
            ),
            "suggestions": ["Zamień wartości base_price i total_price"],
        }

    if has_error:
        error_count = sum(1 for w in warnings if w.get("severity") == "ERROR")
        return {
            "verdict": f"Wykryto {error_count} poważnych problemów cenowych",
            "confidence": "LOW",
            "details": "Sumy cen nie zgadzają się. Wymagana ręczna weryfikacja.",
            "suggestions": ["Sprawdź ręcznie cennik źródłowy"],
        }

    return {
        "verdict": f"Wykryto {len(warnings)} ostrzeżeń",
        "confidence": "MEDIUM",
        "details": "Ceny bazowe wyglądają poprawnie, ale występują drobne niezgodności.",
        "suggestions": ["Zweryfikuj opcje z brakującymi cenami"],
    }


def _build_context(
    validation_dict: dict[str, Any],
    card_summary: dict[str, Any],
) -> str:
    """Build a compact JSON context string for Flash."""
    context = {
        "brand": card_summary.get("brand", ""),
        "model": card_summary.get("model", ""),
        "validation": {
            "is_valid": validation_dict.get("is_valid"),
            "warnings": validation_dict.get("warnings", []),
            "parsed_prices": validation_dict.get("parsed_prices"),
        },
    }
    return json.dumps(context, ensure_ascii=False)


def _call_flash(context_json: str) -> dict[str, Any]:
    """Call Gemini Flash and parse the JSON response."""
    client = get_gemini_client()

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=512,
        response_mime_type="application/json",
        system_instruction=_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    response = client.models.generate_content(
        model=_FLASH_MODEL,
        contents=[types.Part.from_text(text=context_json)],
        config=config,
    )

    raw_text = getattr(response, "text", "{}") or "{}"
    result = json.loads(raw_text)

    # Validate structure
    if "verdict" not in result or "confidence" not in result:
        raise ValueError(f"Unexpected Flash response structure: {result}")

    # Normalize confidence
    confidence = str(result.get("confidence", "MEDIUM")).upper()
    if confidence not in ("HIGH", "MEDIUM", "LOW"):
        confidence = "MEDIUM"
    result["confidence"] = confidence

    # Ensure suggestions is a list
    if not isinstance(result.get("suggestions"), list):
        result["suggestions"] = []

    return result
