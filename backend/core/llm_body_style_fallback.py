"""LLM fallback for body_style → SOT mapping.

Deterministyczny composer (`composite_body_style.compose_body_style`) pokrywa
~95% przypadków — zna mapę 11 kombinacji cabin+zabudowa do SOT canon.
Pozostałe 5% (nowe typy zabudów, nietypowe konfiguracje, sklejone PDF z
nietypowym wording'iem) trafiają do tego modułu jako fallback.

Gemini Flash 2.5 dostaje:
- snapshot card_summary (body_style, service_equipment, vehicle_class)
- listę 32 SOT body_types
- prosi o JSON {body_style: str, confidence: float}

Wyniki są cache'owane w `synthesis_data._composer_llm_resolution` żeby
nie pytać LLM po raz drugi dla tego samego rekordu.

API:
    resolve_body_style_via_llm(card_summary, sot_body_types) → (body_style, confidence)

Returns None if LLM call fails — caller (composer) keeps raw body_style.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from google.genai import types

from core.gemini_client import (
    SAFETY_SETTINGS_PERMISSIVE,
    generate_content_with_retry,
    get_gemini_client,
)
from core.json_utils import clean_json_response

logger = logging.getLogger(__name__)


_PROMPT_TEMPLATE = """Jesteś asystentem klasyfikującym typ nadwozia pojazdu w taksonomii SOT (Source of Truth).

Otrzymujesz aktualne dane pojazdu wyciągnięte z dokumentu (oferta dealera, broszura, zamówienie zabudowy):

DANE POJAZDU:
- body_style (aktualny): {body_style}
- vehicle_class: {vehicle_class}
- service_equipment.name: {se_name}
- service_equipment.components: {se_components}
- powertrain: {powertrain}
- trim_level: {trim_level}

DOSTĘPNE TYPY NADWOZIA w SOT (wybierz dokładnie JEDEN):
{sot_options}

ZADANIE:
Wybierz NAJBARDZIEJ pasujący typ nadwozia z SOT na podstawie kombinacji body_style (typ kabiny/podwozia) i service_equipment (zabudowa). Pamiętaj:
- "Podwozie" + zabudowa typu Kontener Izotermiczny + Agregat Chłodniczy → "Podwozie Izoterma" (aktywna izolacja temperaturowa)
- "Podwozie" + zabudowa Kontener (bez izotermicznego/agregatu) → "Podwozie Kontener" (geometria)
- "Furgon brygadowy" + zabudowa Chłodnia → "Furgon Chłodnia"
- "Podwozie z kabiną brygadową" + zabudowa Skrzynia → "Podwozie Brygadowe Skrzynia"
- Osobówki: Hatchback / Kombi / Sedan / SUV / itp. — gdy nie ma zabudowy

Zwróć WYŁĄCZNIE JSON (bez markdown):
{{
  "body_style": "<dokładnie jedna wartość z listy SOT>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<krótkie uzasadnienie max 200 znaków>"
}}

ZASADA: Jeśli nie masz pewności (confidence < 0.7), zwróć i tak najbliższy wybór + niskie confidence — pipeline dorzuci chip do potwierdzenia przez człowieka.
"""


def _build_prompt(card_summary: dict, sot_body_types: tuple[str, ...]) -> str:
    se = card_summary.get("service_equipment") or {}
    se_name = se.get("name", "—") if isinstance(se, dict) else "—"
    se_comps: list[str] = []
    if isinstance(se, dict):
        for c in se.get("components") or []:
            if isinstance(c, dict):
                cname = c.get("name", "")
                if cname:
                    se_comps.append(cname)
    se_components_text = "; ".join(se_comps) if se_comps else "—"

    return _PROMPT_TEMPLATE.format(
        body_style=card_summary.get("body_style", "—"),
        vehicle_class=card_summary.get("vehicle_class", "—"),
        se_name=se_name,
        se_components=se_components_text,
        powertrain=card_summary.get("powertrain", "—"),
        trim_level=card_summary.get("trim_level", "—"),
        sot_options="\n".join(f"  - {s}" for s in sot_body_types),
    )


def resolve_body_style_via_llm(
    card_summary: dict,
    sot_body_types: tuple[str, ...],
) -> Optional[tuple[str, float]]:
    """Ask Gemini Flash to map current body_style + service_equipment to a SOT
    canon entry.

    Returns (body_style, confidence) on success, or None on any error (caller
    falls back to raw body_style).

    Side effects: none (caller decides whether to apply / cache).
    """
    if not card_summary:
        return None
    try:
        prompt = _build_prompt(card_summary, sot_body_types)
        client = get_gemini_client()
        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=256,
            response_mime_type="application/json",
            safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        )
        response = generate_content_with_retry(
            client=client,
            model="gemini-2.5-flash",
            contents=[types.Part.from_text(text=prompt)],
            config=config,
        )
        raw_text = getattr(response, "text", "") or ""
        if not raw_text:
            logger.warning("[LLM_BODY_STYLE_FALLBACK] Empty response from Gemini")
            return None
        cleaned = clean_json_response(str(raw_text))
        data = json.loads(cleaned)
    except Exception as exc:  # noqa: BLE001 — fallback must never break pipeline
        logger.warning(
            "[LLM_BODY_STYLE_FALLBACK] Gemini call failed: %s", exc
        )
        return None

    body_style = data.get("body_style")
    confidence = data.get("confidence")
    if not isinstance(body_style, str) or body_style not in sot_body_types:
        logger.warning(
            "[LLM_BODY_STYLE_FALLBACK] Returned body_style %r not in SOT",
            body_style,
        )
        return None
    try:
        conf_f = float(confidence) if confidence is not None else 0.5
    except (TypeError, ValueError):
        conf_f = 0.5
    conf_f = max(0.0, min(1.0, conf_f))

    logger.info(
        "[LLM_BODY_STYLE_FALLBACK] Resolved body_style=%r confidence=%.2f reasoning=%r",
        body_style,
        conf_f,
        data.get("reasoning", "")[:200],
    )
    return body_style, conf_f
