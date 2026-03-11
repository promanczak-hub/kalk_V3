"""Feature enrichment pipeline.

Reads card_summary data (standard_equipment, paid_options, direct fields)
from vehicle_synthesis and creates vehicle_feature_evidence records.
Then calls the resolver to build vehicle_feature_state.

Matching strategy: LLM-based semantic matching (Gemini Flash, batch call)
replaces the former deterministic fuzzy substring matcher.  This avoids
false positives such as "Koło zapasowe z felgą aluminiową" being matched
to the feature "felga aluminiowa".
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google.genai import types

from core.database import supabase as sb_client
from core.feature_resolver import resolve_vehicle_features
from core.gemini_client import SAFETY_SETTINGS_PERMISSIVE, get_gemini_client

logger = logging.getLogger(__name__)

# Minimum confidence required to accept an LLM match.
_CONFIDENCE_THRESHOLD = 0.70

# Direct card_summary field → feature_key mappings (unchanged).
_DIRECT_FIELD_MAP: dict[str, str] = {
    "fuel": "paliwo",
    "transmission": "skrzynia_biegow",
    "drive_type": "naped",
    "body_style": "typ_nadwozia",
    "number_of_seats": "liczba_miejsc",
    "has_tow_hook": "hak_holowniczy",
    "is_metalic_paint": "lakier_metalik",
    "has_automatic_ac": "klimatyzacja_automatyczna",
}

# JSON schema returned by the LLM matcher.
_LLM_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "description": (
                "One entry per input equipment item, in the same order."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "Original equipment item name (verbatim).",
                    },
                    "feature_key": {
                        "type": "string",
                        "description": (
                            "Matched feature_key from the catalog, "
                            "or empty string when no match."
                        ),
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Match certainty 0.0–1.0.",
                    },
                },
                "required": ["item", "feature_key", "confidence"],
            },
        },
    },
    "required": ["matches"],
}


def _build_feature_catalog_text(features: list[dict[str, Any]]) -> str:
    """Build a compact text representation of the feature catalog."""
    lines = [
        f"- {f['feature_key']}: {f['display_name']}"
        for f in features
        if f.get("feature_key") and f.get("display_name")
    ]
    return "\n".join(lines)


def _llm_match_equipment(
    equipment_items: list[str],
    features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Batch LLM call: equipment items → matched features.

    Sends all items in a single Gemini Flash call with temperature=0.0
    and structured JSON output.  Returns only matches whose confidence
    meets or exceeds ``_CONFIDENCE_THRESHOLD``.

    Falls back to an empty list on any LLM error (safe degradation —
    the vehicle is enriched without features rather than crashing).

    Parameters
    ----------
    equipment_items:
        Raw names from standard_equipment or paid_options.
    features:
        Rows from ``universal_features`` (need ``feature_key`` + ``display_name``).

    Returns
    -------
    list[dict]
        ``[{"item": str, "feature_key": str, "confidence": float}]``
        — only high-confidence matches.
    """
    if not equipment_items or not features:
        return []

    catalog_text = _build_feature_catalog_text(features)
    items_text = "\n".join(f"- {item}" for item in equipment_items)

    prompt = f"""Jesteś ekspertem klasyfikacji wyposażenia pojazdów.

Poniżej znajduje się katalog cech (feature_key: opis):
{catalog_text}

Przyporządkuj każdą z poniższych pozycji wyposażenia do DOKŁADNIE JEDNEJ cechy z katalogu.
Jeśli pozycja nie pasuje do żadnej cechy z katalogu, zwróć pusty feature_key i confidence=0.0.

WAŻNE ZASADY:
1. Dopasowanie musi być semantycznie dokładne — nie wystarczy, że słowo z opisu cechy
   pojawia się w nazwie pozycji (np. "Koło zapasowe z felgą aluminiową" NIE pasuje do
   cechy "felga_aluminiowa" — to osobna kategoria akcesorium).
2. Każda pozycja oceniana jest NIEZALEŻNIE — nie grupuj ich.
3. Zwróć wyник dla KAŻDEJ pozycji z listy, w tej samej kolejności.

Pozycje wyposażenia do dopasowania:
{items_text}
"""

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=_LLM_RESPONSE_SCHEMA,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )
        resp_text = getattr(response, "text", "{}") or "{}"
        result = json.loads(resp_text)
        matches: list[dict[str, Any]] = result.get("matches", [])

        return [
            m
            for m in matches
            if m.get("feature_key") and m.get("confidence", 0) >= _CONFIDENCE_THRESHOLD
        ]

    except Exception as exc:
        logger.warning(
            "LLM feature matching failed for batch of %d items: %s",
            len(equipment_items),
            exc,
        )
        return []


def _load_feature_catalog() -> list[dict[str, Any]]:
    """Load all active universal_features."""
    resp = (
        sb_client.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key, display_name, feature_type")
        .execute()
    )
    return resp.data or []


def enrich_vehicle_features(
    vehicle_id: str,
    synthesis_data: dict[str, Any],
) -> dict[str, Any]:
    """Extract features from card_summary and create evidence.

    Uses LLM-based semantic matching to map equipment names to universal
    features.  Direct field mappings (fuel, transmission, …) are applied
    separately without LLM involvement.

    Parameters
    ----------
    vehicle_id:
        UUID of the vehicle in ``vehicle_synthesis``.
    synthesis_data:
        Full ``synthesis_data`` JSON from ``vehicle_synthesis``.

    Returns
    -------
    dict
        Summary dict with counts and any errors.
    """
    sb = sb_client
    card_summary = synthesis_data.get("card_summary", {})
    if not isinstance(card_summary, dict):
        return {"error": "No card_summary found", "evidence_created": 0}

    features = _load_feature_catalog()
    if not features:
        return {"error": "Feature catalog empty", "evidence_created": 0}

    feature_by_key: dict[str, str] = {f["feature_key"]: f["id"] for f in features}

    evidence_batch: list[dict[str, Any]] = []

    # ── 1. Standard equipment → LLM match → boolean "present" evidence ──
    std_equipment: list[str] = card_summary.get("standard_equipment", [])
    std_items = [i for i in std_equipment if isinstance(i, str) and i.strip()]

    std_matches = _llm_match_equipment(std_items, features)
    for match in std_matches:
        feat_id = feature_by_key.get(match["feature_key"])
        if not feat_id:
            continue
        evidence_batch.append(
            {
                "source_vehicle_id": vehicle_id,
                "feature_id": feat_id,
                "source_type": "catalog",
                "evidence_status": "observed",
                "value_bool": True,
                "value_text": match["item"],
                "confidence": round(match["confidence"], 4),
            }
        )

    # ── 2. Paid options → LLM match → boolean "present" evidence ──
    paid_options: list[dict] = card_summary.get("paid_options", [])
    opt_names = [
        (opt.get("name") or "").strip()
        for opt in paid_options
        if isinstance(opt, dict) and (opt.get("name") or "").strip()
    ]

    opt_matches = _llm_match_equipment(opt_names, features)
    for match in opt_matches:
        feat_id = feature_by_key.get(match["feature_key"])
        if not feat_id:
            continue
        evidence_batch.append(
            {
                "source_vehicle_id": vehicle_id,
                "feature_id": feat_id,
                "source_type": "price_list",
                "evidence_status": "observed",
                "value_bool": True,
                "value_text": match["item"],
                "confidence": round(match["confidence"], 4),
            }
        )

    # ── 3. Direct field mappings (fuel, transmission, etc.) ──
    for cs_field, feat_key in _DIRECT_FIELD_MAP.items():
        value = card_summary.get(cs_field)
        if value is None:
            continue
        feat_id = feature_by_key.get(feat_key)
        if not feat_id:
            continue

        evidence: dict[str, Any] = {
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_id,
            "source_type": "catalog",
            "evidence_status": "observed",
            "confidence": 0.95,
        }

        if isinstance(value, bool):
            evidence["value_bool"] = value
        elif isinstance(value, (int, float)):
            evidence["value_num"] = float(value)
        else:
            str_val = str(value).strip()
            if str_val.lower() not in ("brak", "none", "null", ""):
                evidence["value_text"] = str_val
            else:
                continue

        evidence_batch.append(evidence)

    # ── 4. Insert evidence (batch upsert) ──
    created_count = 0
    errors: list[str] = []

    if evidence_batch:
        try:
            sb.schema("reverse_search").table("vehicle_feature_evidence").upsert(
                evidence_batch,
                on_conflict="source_vehicle_id,feature_id,source_type",
            ).execute()
            created_count = len(evidence_batch)
        except Exception as exc:
            msg = f"Evidence batch upsert error: {exc}"
            errors.append(msg)
            logger.warning(msg)

    # ── 5. Resolve features ──
    resolve_result: dict[str, Any] = {}
    if created_count > 0:
        resolve_result = resolve_vehicle_features(vehicle_id)

    logger.info(
        "Enriched vehicle %s: %d evidence records, %d errors",
        vehicle_id,
        created_count,
        len(errors),
    )

    return {
        "vehicle_id": vehicle_id,
        "evidence_created": created_count,
        "evidence_matched_from": {
            "standard_equipment": len(std_items),
            "paid_options": len(opt_names),
            "direct_fields": len(_DIRECT_FIELD_MAP),
        },
        "resolve_result": resolve_result,
        "errors": errors,
    }


def enrich_all_vehicles(
    limit: int = 100,
) -> dict[str, Any]:
    """Batch-enrich all vehicles that have card_summary data."""
    sb = sb_client

    resp = (
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .not_.is_("synthesis_data", "null")
        .limit(limit)
        .execute()
    )
    vehicles = resp.data or []

    results: list[dict[str, Any]] = []
    total_evidence = 0
    total_errors = 0

    for v in vehicles:
        synthesis = v.get("synthesis_data")
        if not isinstance(synthesis, dict):
            continue
        if not isinstance(synthesis.get("card_summary"), dict):
            continue

        result = enrich_vehicle_features(v["id"], synthesis)
        results.append(result)
        total_evidence += result.get("evidence_created", 0)
        total_errors += len(result.get("errors", []))

    return {
        "vehicles_processed": len(results),
        "total_evidence_created": total_evidence,
        "total_errors": total_errors,
        "per_vehicle": results,
    }
