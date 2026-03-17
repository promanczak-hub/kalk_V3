"""LLM-based variant matching and catalog ranking.

Contains prompts, deterministic price-matching, and Gemini Flash calls.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.cross_ref_models import (
    CatalogRankingResult,
    CrossRefLLMError,
    VariantMatchResult,
)
from core.gemini_client import SAFETY_SETTINGS_PERMISSIVE, get_gemini_client

try:
    from google.genai import types  # type: ignore[import-untyped]
except ImportError:
    types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ── Prompts ──────────────────────────────────────────────────────

CROSS_REF_SYSTEM_PROMPT = """\
Jesteś ekspertem ds. pojazdów dostawczych i osobowych. Otrzymujesz:
1. `vehicle_spec` — podsumowanie i dane pojazdu (marka, model, silnik, wymiary, wersja wyposażenia / trim_level)
2. `catalog_variants` — lista wariantów wyciągniętych z dopasowanych katalogów/cenników z ich parametrami i wyposażeniem
3. `available_feature_keys` — lista kluczy cech w systemie

ZADANIE:
A) Dopasuj pojazd do NAJLEPSZEGO wariantu z katalogu stosując ocenę prawdopodobieństwa (probabilistyczną):
   1. Idealnie (Score 0.95 - 1.0): Marka, model, silnik i DOKŁADNA wersja wyposażenia (trim_level) pasują perfekcyjnie.
   2. Wysoce prawdopodobnie (Score 0.80 - 0.94): Brakuje części nazwy lub dokładnego znacznika (np. brakuje "eDrive", "130"), ale bazowa nazwa wyposażenia (np. "Essence" zamiast "Edition 130") lub parametry silnika/nadwozia zgadzają się na tyle, że cechy standardowe dla tego wariantu mogą być bezpiecznie przypisane do pojazdu. 
   3. Akceptowalnie (Score 0.65 - 0.79): Wersja się nieco różni, ale większość kluczowych parametrów wskazuje na silne prawdopodobieństwo, że wyposażenie standardowe pokrewnych wersji jest zbliżone.
   4. Brak związku (Score < 0.65): Zupełnie inna bazowa wersja wyposażenia (np. badasz najwyższą wersję, a cennik ma tylko wersję podstawową) lub niezgodny model/marka. Ustaw wtedy `matched_variant_name` na "Brak dopasowania w katalogu" i pustą listę `features`.

B) Wyciągnij z dopasowanego wariantu WSZYSTKIE użyteczne cechy należące do STANDARDU TEJ WERSJI lub zadeklarowanych w specyfikacji opcji i zmapuj je na klucze z `available_feature_keys`.
   Cechy numeryczne podaj w odpowiednich jednostkach (mm, kg, l, szt). Oszacuj `mapping_confidence` (0.0 - 1.0) dla dokładności mapowania samej cechy (tylko wysokiej pewności mapowania cech >= 0.90 będą akceptowane przez system).

C) Wymiary ładunkowe/zewnętrzne potraktuj absolutnie priorytetowo jako osobne cechy, jeśli występują.

ZASADY:
- NIE jesteś zero-jedynkowy: jeśli wersja w specyfikacji to "Edition 130", a w katalogu jest tylko "Essence", i parametry techniczne są bardzo zbliżone, możesz dopasować ten wariant z `confidence` około 0.85 i uzasadnić to w `reasoning` (np. "Wariant 'Essence' ma częściowe pokrycie opcji z badaną wersją 'Edition 130'").
- `confidence` zwracasz jako ocenę całościową dla wybranego wariantu.
- Uzasadnienie (`reasoning`) MUSI krótko tłumaczyć dlaczego przyznałeś taki score (np. "Zgodność silnika i bazowej wersji, brak precyzyjnego tagu obniża pewność").
- Zwracaj w features tylko cechy realnie pasujące do wybranego wariantu.
"""  # noqa: E501

RANKING_SYSTEM_PROMPT = """\
Jesteś asystentem pomagającym wybrać najlepszy cennik/katalog dla konkretnego pojazdu.
Otrzymujesz:
1. `vehicle_spec` — dane pojazdu (marka, model, wersja, silnik).
2. `available_catalogs` — listę dostępnych dokumentów w systemie.

ZADANIE:
Oceń każdy dokument pod kątem tego, jak precyzyjnie opisuje podany pojazd. 
1. `relevance_score` = 1.0 oznacza idealne dopasowanie (ta sama marka, model i generacja/rok z tagu wersji).
2. `relevance_score` = 0.0 oznacza brak związku (inna marka/model).
3. Posortuj dokumenty od najbardziej trafnych do namniej trafnych.

Zwróć wynik jako listę w polu `rankings`.
"""


# ── Deterministic price matching ─────────────────────────────────


def find_exact_variant_match(
    vehicle_spec: dict[str, Any],
    catalog_variants: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find a 100% deterministic match based on price and name."""
    base_price = vehicle_spec.get("base_price")
    try:
        if base_price is not None:
            # Handle string prices like "222800 PLN brutto" or "222 800,50"
            price_str = str(base_price).replace(" ", "").replace(",", ".")
            import re
            match = re.search(r"[\d.]+", price_str)
            base_price_float = float(match.group(0)) if match else 0.0
        else:
            base_price_float = 0.0
    except (ValueError, TypeError):
        base_price_float = 0.0

    trim_level = str(vehicle_spec.get("trim_level") or "").strip().lower()
    power_hp = vehicle_spec.get("power_hp")

    if base_price_float <= 0:
        return None

    best_match: dict[str, Any] | None = None
    for variant in catalog_variants:
        v_price_net = variant.get("price_net")
        v_price_gross = variant.get("price_gross")

        try:
            p_net = float(v_price_net) if v_price_net is not None else 0.0
            p_gross = (
                float(v_price_gross) if v_price_gross is not None else 0.0
            )
        except (ValueError, TypeError):
            continue

        is_price_match = False
        if p_net > 0 and abs(p_net - base_price_float) < 1.0:
            is_price_match = True
        elif p_gross > 0 and abs(p_gross - base_price_float) < 1.0:
            is_price_match = True

        if is_price_match:
            variant_name = str(
                variant.get("variant_name") or ""
            ).strip().lower()
            is_trim_match = bool(trim_level and trim_level in variant_name)
            is_power_match = bool(
                power_hp and str(power_hp) in variant_name
            )

            if is_trim_match or is_power_match:
                return variant  # Perfect match with name or power

            if not best_match:
                best_match = variant

    return best_match


# ── LLM variant matching ────────────────────────────────────────


def match_variant_with_llm(
    vehicle_spec: dict[str, Any],
    catalog_variants: list[dict[str, Any]],
    feature_keys: list[str],
) -> VariantMatchResult:
    """Use LLM Flash to match vehicle spec to catalog variant.

    Raises:
        CrossRefLLMError: When LLM call fails (infrastructure error).
    """
    if types is None:
        raise CrossRefLLMError("google.genai not available")

    client = get_gemini_client()

    user_content = json.dumps(
        {
            "vehicle_spec": vehicle_spec,
            "catalog_variants": catalog_variants,
            "available_feature_keys": feature_keys,
        },
        ensure_ascii=False,
        indent=2,
    )

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=VariantMatchResult,
        system_instruction=CROSS_REF_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[user_content],
            config=config,
        )
        text = getattr(response, "text", "{}") or "{}"
        data = json.loads(text)
        return VariantMatchResult(**data)
    except Exception as exc:
        raise CrossRefLLMError(f"LLM cross-reference failed: {exc}") from exc


# ── LLM catalog ranking ─────────────────────────────────────────


def rank_catalogs_for_vehicle(
    vehicle_spec: dict[str, Any],
    catalogs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Use LLM Flash to rank catalogs for a specific vehicle.

    Returns the original catalogs list, sorted by relevance score
    descending, with an added `_ranking` dict containing score and
    reasoning. Does NOT mutate original dicts — copies are returned.
    """
    if not catalogs:
        return []

    if types is None:
        logger.error(
            "google.genai not available. Returning unsorted catalogs."
        )
        return catalogs

    client = get_gemini_client()

    user_content = json.dumps(
        {
            "vehicle_spec": vehicle_spec,
            "available_catalogs": [
                {
                    "id": c["id"],
                    "brand": c["brand"],
                    "model_family": c["model_family"],
                    "display_name": c["display_name"],
                    "version_tag": c["version_tag"],
                    "file_type": c["file_type"],
                }
                for c in catalogs
            ],
        },
        ensure_ascii=False,
        indent=2,
    )

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=4096,
        response_mime_type="application/json",
        response_schema=CatalogRankingResult,
        system_instruction=RANKING_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[user_content],
            config=config,
        )
        text = getattr(response, "text", "{}") or "{}"
        data = json.loads(text)
        ranking_result = CatalogRankingResult(**data)

        score_map = {r.catalog_id: r for r in ranking_result.rankings}

        for cat in catalogs:
            extracted = cat.get("extracted_data") or {}
            variants = extracted.get("variants", [])
            exact_variant = find_exact_variant_match(vehicle_spec, variants)

            if exact_variant:
                cat["_ranking"] = {
                    "score": 1.0,
                    "reasoning": (
                        f"Znaleziono idealne dopasowanie 100% wariantu "
                        f"({exact_variant.get('variant_name')}) na podstawie "
                        f"zgodności ceny (co do 1 PLN)."
                    ),
                }
                continue

            rank_data = score_map.get(cat["id"])
            if rank_data:
                cat["_ranking"] = {
                    "score": rank_data.relevance_score,
                    "reasoning": rank_data.reasoning,
                }
            else:
                cat["_ranking"] = {
                    "score": 0.0,
                    "reasoning": "LLM omitted this item",
                }

        catalogs.sort(
            key=lambda x: x.get("_ranking", {}).get("score", 0.0),
            reverse=True,
        )
        return catalogs

    except Exception as exc:
        logger.error("LLM catalog ranking failed: %s", exc)
        return catalogs
