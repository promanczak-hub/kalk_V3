"""Feature enrichment pipeline.

Reads card_summary data (standard_equipment, paid_options, direct fields)
from vehicle_synthesis and creates vehicle_feature_evidence records.
Then calls the resolver to build vehicle_feature_state.

This is the bridge between extraction pipeline and universal features.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from core.database import supabase as sb_client
from core.feature_resolver import resolve_vehicle_features

logger = logging.getLogger(__name__)

# Direct card_summary field → feature_key mappings
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


def _normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching."""
    text = unicodedata.normalize("NFKD", text)
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def _build_feature_index(
    features: list[dict[str, Any]],
    aliases: list[dict[str, Any]],
) -> dict[str, str]:
    """Build normalized_text → feature_id index.

    Includes both display_name and alias texts.
    """
    index: dict[str, str] = {}

    for feat in features:
        display = _normalize_text(feat.get("display_name", ""))
        if display:
            index[display] = feat["id"]

        key = feat.get("feature_key", "")
        if key:
            index[key] = feat["id"]

    for alias in aliases:
        normalized = alias.get("normalized_alias", "")
        if normalized:
            index[normalized.strip().lower()] = alias["feature_id"]

        alias_text = _normalize_text(alias.get("alias_text", ""))
        if alias_text:
            index[alias_text] = alias["feature_id"]

    return index


def _fuzzy_match(
    equipment_name: str,
    feature_index: dict[str, str],
) -> str | None:
    """Try to match an equipment name to a feature_id.

    Strategy:
    1. Exact normalized match
    2. Substring match (equipment_name contains feature name)
    3. Substring match (feature name contains equipment_name)
    """
    normalized = _normalize_text(equipment_name)
    if not normalized:
        return None

    # 1. Exact match
    if normalized in feature_index:
        return feature_index[normalized]

    # 2. Equipment name contains a feature name
    best_match: str | None = None
    best_length = 0
    for feat_text, feat_id in feature_index.items():
        if len(feat_text) < 4:
            continue
        if feat_text in normalized and len(feat_text) > best_length:
            best_match = feat_id
            best_length = len(feat_text)

    if best_match and best_length >= 5:
        return best_match

    # 3. Feature name contains equipment name (only if eq name long enough)
    if len(normalized) >= 6:
        for feat_text, feat_id in feature_index.items():
            if normalized in feat_text:
                return feat_id

    return None


def _load_feature_catalog() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Load all universal_features and their aliases."""
    sb = sb_client

    features_resp = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key, display_name, feature_type")
        .execute()
    )
    features: list[dict[str, Any]] = features_resp.data or []

    aliases_resp = (
        sb.schema("reverse_search")
        .table("universal_feature_aliases")
        .select("feature_id, alias_text, normalized_alias")
        .execute()
    )
    aliases: list[dict[str, Any]] = aliases_resp.data or []

    return features, aliases


def enrich_vehicle_features(
    vehicle_id: str,
    synthesis_data: dict[str, Any],
) -> dict[str, Any]:
    """Extract features from card_summary and create evidence.

    Args:
        vehicle_id: UUID of the vehicle.
        synthesis_data: Full synthesis_data JSON from vehicle_synthesis.

    Returns:
        Summary dict with counts.
    """
    sb = sb_client
    card_summary = synthesis_data.get("card_summary", {})
    if not isinstance(card_summary, dict):
        return {"error": "No card_summary found", "evidence_created": 0}

    # Load feature catalog
    features, aliases = _load_feature_catalog()
    if not features:
        return {"error": "Feature catalog empty", "evidence_created": 0}

    # Build lookup
    feature_index = _build_feature_index(features, aliases)
    feature_by_key: dict[str, str] = {f["feature_key"]: f["id"] for f in features}

    evidence_batch: list[dict[str, Any]] = []

    # ── 1. Standard equipment → boolean "present" evidence
    std_equipment = card_summary.get("standard_equipment", [])
    if isinstance(std_equipment, list):
        for item_name in std_equipment:
            if not isinstance(item_name, str) or not item_name.strip():
                continue
            feature_id = _fuzzy_match(item_name, feature_index)
            if feature_id:
                evidence_batch.append(
                    {
                        "source_vehicle_id": vehicle_id,
                        "feature_id": feature_id,
                        "source_type": "catalog",
                        "evidence_status": "observed",
                        "value_bool": True,
                        "value_text": item_name.strip(),
                        "confidence": 0.85,
                    }
                )

    # ── 2. Paid options → boolean "present" evidence
    paid_options = card_summary.get("paid_options", [])
    if isinstance(paid_options, list):
        for opt in paid_options:
            if not isinstance(opt, dict):
                continue
            name = (opt.get("name") or "").strip()
            if not name:
                continue
            feature_id = _fuzzy_match(name, feature_index)
            if feature_id:
                evidence_batch.append(
                    {
                        "source_vehicle_id": vehicle_id,
                        "feature_id": feature_id,
                        "source_type": "price_list",
                        "evidence_status": "observed",
                        "value_bool": True,
                        "value_text": name,
                        "confidence": 0.9,
                    }
                )

    # ── 3. Direct field mappings (fuel, transmission, etc.)
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

    # ── 4. Insert evidence (batch upsert)
    created_count = 0
    errors: list[str] = []

    for ev in evidence_batch:
        try:
            sb.schema("reverse_search").table("vehicle_feature_evidence").upsert(
                ev,
                on_conflict="source_vehicle_id,feature_id,source_type",
            ).execute()
            created_count += 1
        except Exception as e:
            msg = f"Evidence insert error: {e}"
            errors.append(msg)
            logger.warning(msg)

    # ── 5. Resolve features
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
            "standard_equipment": len(std_equipment)
            if isinstance(std_equipment, list)
            else 0,
            "paid_options": len(paid_options) if isinstance(paid_options, list) else 0,
            "direct_fields": len(_DIRECT_FIELD_MAP),
        },
        "resolve_result": resolve_result,
        "errors": errors,
    }


def enrich_all_vehicles(
    limit: int = 100,
) -> dict[str, Any]:
    """Batch-enrich all vehicles that have card_summary data.

    Returns summary with per-vehicle stats.
    """
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

        card_summary = synthesis.get("card_summary")
        if not isinstance(card_summary, dict):
            continue

        vehicle_id = v["id"]
        result = enrich_vehicle_features(vehicle_id, synthesis)
        results.append(result)
        total_evidence += result.get("evidence_created", 0)
        total_errors += len(result.get("errors", []))

    return {
        "vehicles_processed": len(results),
        "total_evidence_created": total_evidence,
        "total_errors": total_errors,
        "per_vehicle": results,
    }
