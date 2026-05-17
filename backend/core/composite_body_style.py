"""Compose final body_style from cabin signal + zabudowa signal.

The AI extractor (see prompts.py) by design splits two signals:
- `card_summary.body_style` carries cabin/chassis info ("Podwozie z kabiną brygadową").
- `card_summary.service_equipment.name` carries zabudowa info ("Zabudowa skrzynia ...").

Neither field alone matches the SOT canon (see model_normalizer.SOT_BODY_TYPES),
which encodes business templates from arkusz Szablon_Wyceny_GCP, e.g.
"Podwozie Brygadowe Skrzynia". This module joins the two signals into the
composite SOT name when both are present.

Keeps an own copy of zabudowa keywords because ltr_vehicle_resolvers.py is a
frozen module.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

# Mirror of ltr_vehicle_resolvers._ZABUDOWA_KEYWORDS (frozen module).
# Keys are SOT zabudowa categories; values are detection keywords (UPPER).
# WYWROTKA added — missing in resolvers but in SOT.
_ZABUDOWA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "SKRZYNIA": ("SKRZYNIA", "SKRZYNI", "DROPSIDE"),
    "KONTENER": ("KONTENER", "BOX BODY", " BOX "),
    "WYWROTKA": ("WYWROTKA", "WYWROTK", "TIPPER", "DUMPER"),
    "PLANDEKA": ("PLANDEKA", "PLANDEK", "TARPAULIN", "CURTAINSIDER"),
    "CHLODNIA": ("CHLODNIA", "CHLODNI", "CHŁODNIA", "CHŁODNI", "CHILLER", "REEFER"),
    "IZOTERMA": ("IZOTERMA", "IZOTERM", "ISOTHERM"),
}

# Composite output table. Key = (cabin_kind, zabudowa_key) → SOT body_style.
# cabin_kind: "podwozie_brygadowe" | "podwozie" | "furgon" | "furgon_brygadowy"
_COMPOSITE_TABLE: dict[tuple[str, str], str] = {
    ("podwozie_brygadowe", "SKRZYNIA"): "Podwozie Brygadowe Skrzynia",
    ("podwozie_brygadowe", "KONTENER"): "Podwozie Brygadowe Kontener",
    ("podwozie_brygadowe", "WYWROTKA"): "Podwozie Brygadowe Wywrotka",
    ("podwozie_brygadowe", "PLANDEKA"): "Podwozie Brygadowe Plandeka",
    ("podwozie", "SKRZYNIA"): "Podwozie Skrzynia",
    ("podwozie", "KONTENER"): "Podwozie Kontener",
    ("podwozie", "WYWROTKA"): "Podwozie Wywrotka",
    ("podwozie", "PLANDEKA"): "Podwozie Plandeka",
    ("podwozie", "CHLODNIA"): "Podwozie Chłodnia",
    ("podwozie", "IZOTERMA"): "Podwozie Izoterma",
    ("furgon", "CHLODNIA"): "Furgon Chłodnia",
}


def _classify_cabin(body_style: str) -> Optional[str]:
    """Detect cabin/chassis kind from raw body_style.

    Returns one of: "podwozie_brygadowe" | "podwozie" | "furgon_brygadowy" |
    "furgon" — or None if neither chassis nor furgon is signalled.
    """
    if not body_style:
        return None
    text = body_style.lower()
    has_brygada = "brygad" in text  # 'brygadowa', 'brygadowy', 'brygadową', etc.
    has_podwozie = "podwozie" in text
    has_furgon = "furgon" in text

    if has_podwozie and has_brygada:
        return "podwozie_brygadowe"
    if has_furgon and has_brygada:
        return "furgon_brygadowy"
    if has_podwozie:
        return "podwozie"
    if has_furgon:
        return "furgon"
    return None


def _detect_zabudowa_from_text(text: str) -> Optional[str]:
    """Match a single text against zabudowa keywords. Returns SOT key or None."""
    if not text:
        return None
    upper = text.upper()
    for key, keywords in _ZABUDOWA_KEYWORDS.items():
        for kw in keywords:
            if kw in upper:
                return key
    return None


def _detect_zabudowa(service_equipment: Any) -> Optional[str]:
    """Detect zabudowa SOT key from service_equipment dict.

    Looks at the main `name` first, then iterates through `components[].name`.
    Returns first match by iteration order.
    """
    if not isinstance(service_equipment, Mapping):
        return None

    main_name = str(service_equipment.get("name") or "")
    detected = _detect_zabudowa_from_text(main_name)
    if detected:
        return detected

    components = service_equipment.get("components") or []
    if isinstance(components, list):
        for comp in components:
            if isinstance(comp, Mapping):
                comp_name = str(comp.get("name") or "")
                detected = _detect_zabudowa_from_text(comp_name)
                if detected:
                    return detected
    return None


def _promote_kontener(body_style: Optional[str], service_equipment: Any) -> str:
    """KONTENER is geometry; IZOTERMA / CHLODNIA are temperature categories.

    When 'izoterm' / 'isotherm' appears anywhere in body_style or service_equipment
    text → return IZOTERMA. When 'chlodni' / 'chiller' / 'reefer' appears
    (without izoterm) → CHLODNIA. Otherwise stay KONTENER.

    Rationale: AI often labels a refrigerated container as just "Kontener" even
    when the components list calls it "Kontener Izotermiczny" + "Agregat
    Chłodniczy". SOT distinguishes these as separate body types.
    """
    blob = (body_style or "").upper()
    if isinstance(service_equipment, Mapping):
        blob += " " + str(service_equipment.get("name") or "").upper()
        for comp in service_equipment.get("components") or []:
            if isinstance(comp, Mapping):
                blob += " " + str(comp.get("name") or "").upper()

    if any(kw in blob for kw in ("IZOTERM", "ISOTHERM")):
        return "IZOTERMA"
    if any(kw in blob for kw in ("CHŁODNI", "CHLODNI", "CHILLER", "REEFER")):
        return "CHLODNIA"
    return "KONTENER"


def compose_body_style(
    body_style: Optional[str],
    service_equipment: Any,
    enable_llm_fallback: bool = False,
    card_summary: Optional[dict] = None,
) -> Optional[str]:
    """Return SOT composite body_style if cabin + zabudowa signals combine.

    Strategy:
    1. Try deterministic composer (handles ~95% cases via cabin/zabudowa
       signal detection + composite table lookup).
    2. If result is not in SOT and enable_llm_fallback=True, ask Gemini Flash
       to map the raw body_style + service_equipment to the closest SOT entry.
    3. Otherwise return the deterministic result (raw body_style for unmatched).

    Special cases handled by deterministic step:
    - "Furgon brygadowy" (cabin only, no zabudowa) → "Furgon brygadowy" (SOT).
    - "Podwozie z kabiną brygadową" (cabin only, no zabudowa) → raw preserved.
    - Body_style leak (AI puts zabudowa into body_style, e.g. "Kontener"):
      detect zabudowa keyword in body_style and assume "podwozie" cabin.
    - KONTENER + izoterm/agregat signals → promoted to IZOTERMA.
    """
    if not body_style:
        return body_style

    deterministic_result = _compose_deterministic(body_style, service_equipment)

    # Try LLM fallback if deterministic didn't land in SOT canon
    try:
        from core.model_normalizer import SOT_BODY_TYPES
    except ImportError:  # pragma: no cover
        SOT_BODY_TYPES = ()

    if deterministic_result in SOT_BODY_TYPES:
        return deterministic_result

    if enable_llm_fallback:
        cs_for_llm = card_summary
        if cs_for_llm is None:
            # Build minimal cs for LLM if caller didn't pass one
            cs_for_llm = {
                "body_style": body_style,
                "service_equipment": service_equipment,
            }
        resolved = _try_llm_fallback(cs_for_llm)
        if resolved is not None:
            return resolved

    return deterministic_result


def _compose_deterministic(
    body_style: Optional[str], service_equipment: Any
) -> Optional[str]:
    """Original deterministic composer logic — extracted for testability and
    so LLM fallback can wrap it cleanly."""
    if not body_style:
        return body_style

    cabin = _classify_cabin(body_style)
    zabudowa = _detect_zabudowa(service_equipment)

    if cabin is None:
        zabudowa_in_body = _detect_zabudowa_from_text(body_style)
        if zabudowa_in_body:
            cabin = "podwozie"
            if zabudowa is None:
                zabudowa = zabudowa_in_body

    if cabin is None:
        return body_style

    if zabudowa == "KONTENER":
        zabudowa = _promote_kontener(body_style, service_equipment)

    if zabudowa is None:
        if cabin == "furgon_brygadowy":
            return "Furgon brygadowy"
        return body_style

    if cabin == "furgon_brygadowy":
        composite = _COMPOSITE_TABLE.get(("furgon", zabudowa))
        return composite or body_style

    composite = _COMPOSITE_TABLE.get((cabin, zabudowa))
    return composite or body_style


def _try_llm_fallback(card_summary: dict) -> Optional[str]:
    """Wywołuje Gemini Flash dla mapowania body_style → SOT.

    Failure-tolerant: wszystkie błędy (import, network, parsing) → None,
    pipeline kontynuuje z raw body_style. Lejek dostanie chip
    body_style_not_in_sot jako safety net.
    """
    try:
        from core.llm_body_style_fallback import resolve_body_style_via_llm
        from core.model_normalizer import SOT_BODY_TYPES

        result = resolve_body_style_via_llm(card_summary, SOT_BODY_TYPES)
    except Exception as exc:  # noqa: BLE001 — fallback must never break pipeline
        logger.warning("[COMPOSER] LLM fallback raised: %s", exc)
        return None

    if result is None:
        return None
    body_style, confidence = result
    if confidence < 0.7:
        logger.info(
            "[COMPOSER] LLM fallback low confidence %.2f for body_style=%r — "
            "keeping raw, lejek dostanie chip do potwierdzenia",
            confidence,
            body_style,
        )
        return None
    logger.info(
        "[COMPOSER] LLM fallback resolved body_style=%r (confidence=%.2f)",
        body_style,
        confidence,
    )
    return body_style
