"""Cross-reference vehicle features from multiple catalog sources.

Orchestrator module — delegates to sub-modules:
- cross_ref_models: Pydantic schemas
- cross_ref_llm: LLM matching + catalog ranking
- cross_ref_evidence: Evidence batch creation

Public API (re-exported for backward compatibility):
- cross_reference_vehicle()
- wipe_vehicle_features()
- rank_catalogs_for_vehicle()
- find_exact_variant_match()
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from core.cross_ref_evidence import (
    create_body_param_evidence,
    create_evidence_batch,
    save_catalog_match,
)
from core.cross_ref_llm import (
    find_exact_variant_match,
    match_variant_with_llm,
    rank_catalogs_for_vehicle,
)
from core.cross_ref_models import CrossRefLLMError, VariantMatchResult
from core.database import supabase as sb_client
from core.feature_resolver import resolve_vehicle_features

logger = logging.getLogger(__name__)

# Re-exports for backward compatibility (callers import from here)
__all__ = [
    "cross_reference_vehicle",
    "find_exact_variant_match",
    "rank_catalogs_for_vehicle",
    "wipe_vehicle_features",
]


# ── Feature catalog (single query, cached) ──────────────────────


@lru_cache(maxsize=1)
def _load_feature_catalog() -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    """Load feature keys and id map in a single DB query.

    Returns immutable tuples for lru_cache compatibility.
    """
    resp = (
        sb_client.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key")
        .eq("is_active", True)
        .execute()
    )
    rows = resp.data or []
    keys = tuple(r["feature_key"] for r in rows)
    id_pairs = tuple((r["feature_key"], r["id"]) for r in rows)
    return keys, id_pairs


def _get_feature_keys() -> list[str]:
    """Get active feature keys (convenience wrapper)."""
    keys, _ = _load_feature_catalog()
    return list(keys)


def _get_feature_id_map() -> dict[str, str]:
    """Get feature_key → feature_id mapping (convenience wrapper)."""
    _, id_pairs = _load_feature_catalog()
    return dict(id_pairs)


# ── Wipe features ───────────────────────────────────────────────


def wipe_vehicle_features(
    vehicle_id: str,
    source_type: str | None = None,
) -> dict[str, int]:
    """Delete all evidence and state for a vehicle.

    Args:
        vehicle_id: UUID of the vehicle.
        source_type: If set, only delete evidence from this source.
            State is still fully rebuilt after deletion.

    Returns:
        Counts of deleted evidence and state records.
    """
    sb = sb_client
    evidence_deleted = 0
    state_deleted = 0

    ev_query = (
        sb.schema("reverse_search")
        .table("vehicle_feature_evidence")
        .delete()
        .eq("source_vehicle_id", vehicle_id)
    )
    if source_type:
        ev_query = ev_query.eq("source_type", source_type)

    try:
        resp = ev_query.execute()
        evidence_deleted = len(resp.data or [])
    except Exception as exc:
        logger.error("Evidence delete error: %s", exc)

    try:
        resp = (
            sb.schema("reverse_search")
            .table("vehicle_specs_normalized")
            .delete()
            .eq("vehicle_id", vehicle_id)
            .execute()
        )
        state_deleted = len(resp.data or [])
    except Exception as exc:
        logger.error("State delete error: %s", exc)

    if not source_type:
        try:
            sb.schema("reverse_search").table("vehicle_catalog_matches").delete().eq(
                "source_vehicle_id", vehicle_id
            ).execute()
        except Exception as exc:
            logger.warning("Catalog match delete error: %s", exc)

    logger.info(
        "Wiped features for %s: %d evidence, %d state",
        vehicle_id,
        evidence_deleted,
        state_deleted,
    )

    # Invalidate Redis cache for feature state
    from core.redis_cache import _get_client, _PREFIX

    client = _get_client()
    if client is not None:
        try:
            cache_key = f"{_PREFIX}features_state:{vehicle_id}"
            client.delete(cache_key)
            logger.debug("Invalidated Redis cache for %s", cache_key)
        except Exception as exc:
            logger.warning("Failed to invalidate cache for %s: %s", vehicle_id, exc)

    return {
        "evidence_deleted": evidence_deleted,
        "state_deleted": state_deleted,
    }


# ── Main entry point ────────────────────────────────────────────


def cross_reference_vehicle(
    vehicle_id: str,
    catalog_ids: list[str],
) -> dict[str, Any]:
    """Cross-reference vehicle with selected catalogs.

    Args:
        vehicle_id: UUID of the vehicle.
        catalog_ids: List of catalog UUIDs to match against.

    Returns:
        Summary with matched variants and created evidence.
    """
    sb = sb_client

    # 1. Load vehicle card_summary
    v_resp = (
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data, document_category")
        .eq("id", vehicle_id)
        .limit(1)
        .execute()
    )
    if not v_resp.data:
        return {"error": f"Vehicle {vehicle_id} not found"}

    synthesis = v_resp.data[0].get("synthesis_data") or {}

    # Determine if commercial for body parameter logic
    doc_cat = v_resp.data[0].get("document_category")
    if doc_cat:
        is_commercial = doc_cat == "commercial"
    else:
        v_class_lower = (
            synthesis.get("card_summary", {}).get("vehicle_class", "").lower()
        )
        b_style_lower = synthesis.get("card_summary", {}).get("body_style", "").lower()
        comm_kws = [
            "dostawcz",
            "van",
            "furgon",
            "pick-up",
            "skrzyni",
            "kontener",
            "chłodnia",
            "izoterma",
            "plandeka",
            "podwozie",
            "autolaweta",
        ]
        pass_kws = ["minivan", "microvan", "kombivan"]
        has_comm = any(k in v_class_lower or k in b_style_lower for k in comm_kws)
        has_pass = any(k in v_class_lower or k in b_style_lower for k in pass_kws)
        is_commercial = has_comm and not has_pass

    card_summary = synthesis.get("card_summary", {})
    if not card_summary:
        return {"error": "Vehicle has no card_summary"}

    vehicle_spec = _build_vehicle_spec(card_summary, synthesis)

    # 2. Load catalog variants (without mutating originals)
    all_variants, variant_catalog_ids = _load_catalog_variants(catalog_ids)
    if not all_variants:
        return {"error": "No ready variants found in selected catalogs"}

    # 3. Load feature keys + ID map (single query, cached)
    feature_keys = _get_feature_keys()
    feature_id_map = _get_feature_id_map()

    # 4. LLM variant matching (or exact match bypass)
    match_result = _perform_matching(vehicle_spec, all_variants, feature_keys)
    if isinstance(match_result, dict):
        return match_result  # error dict

    # 5. Create evidence from matched features (batch)
    evidence_count = create_evidence_batch(
        vehicle_id, match_result, feature_id_map, "catalog"
    )

    # 6. Body parameter calculations (batch)
    body_count = create_body_param_evidence(
        vehicle_id,
        match_result,
        feature_id_map,
        is_commercial=is_commercial,
    )

    # 7. Save audit trail (use catalog_id from variant)
    matched_cat_id = _resolve_catalog_id(match_result, variant_catalog_ids, catalog_ids)
    if matched_cat_id:
        save_catalog_match(vehicle_id, matched_cat_id, match_result)

    # 8. Resolve features (merge all evidence)
    resolve_result = resolve_vehicle_features(vehicle_id)

    return {
        "status": "matched",
        "matched_variant": match_result.matched_variant_name,
        "confidence": match_result.confidence,
        "reasoning": match_result.reasoning,
        "evidence_created": evidence_count,
        "body_params_created": body_count,
        "features_extracted": len(match_result.features),
        "resolve_result": resolve_result,
    }


def preview_catalog_features(
    vehicle_id: str,
    catalog_id: str,
) -> dict[str, Any]:
    """Preview features that would be matched from a catalog.

    Does NOT save any evidence or state. Just runs the matching.
    """
    sb = sb_client

    v_resp = (
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .limit(1)
        .execute()
    )
    if not v_resp.data:
        return {"error": f"Vehicle {vehicle_id} not found"}

    synthesis = v_resp.data[0].get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary", {})
    if not card_summary:
        return {"error": "Vehicle has no card_summary"}

    vehicle_spec = _build_vehicle_spec(card_summary, synthesis)

    all_variants, _ = _load_catalog_variants([catalog_id])
    if not all_variants:
        return {"error": "No ready variants found in selected catalog"}

    feature_keys = _get_feature_keys()

    match_result = _perform_matching(vehicle_spec, all_variants, feature_keys)
    if isinstance(match_result, dict):
        return match_result

    # model_dump is pydantic v2
    features_dicts = [
        f.model_dump() if hasattr(f, "model_dump") else f.dict()
        for f in match_result.features
    ]

    return {
        "status": "preview_ready",
        "matched_variant": match_result.matched_variant_name,
        "confidence": match_result.confidence,
        "reasoning": match_result.reasoning,
        "features": features_dicts,
    }


# ── Private helpers ──────────────────────────────────────────────


def _build_vehicle_spec(
    card_summary: dict[str, Any],
    synthesis: dict[str, Any],
) -> dict[str, Any]:
    """Build vehicle spec dict from card_summary + synthesis."""
    return {
        "brand": (card_summary.get("brand") or synthesis.get("brand", "")),
        "model": (card_summary.get("model") or synthesis.get("model", "")),
        "body_style": card_summary.get("body_style", ""),
        "powertrain": card_summary.get("powertrain", ""),
        "power_hp": card_summary.get("power_hp"),
        "drive_type": card_summary.get("drive_type", ""),
        "transmission": card_summary.get("transmission", ""),
        "vehicle_class": card_summary.get("vehicle_class", ""),
        "trim_level": card_summary.get("trim_level", ""),
        "base_price": (
            card_summary.get("base_price")
            or synthesis.get("pricing", {}).get("base_price")
        ),
    }


def _load_catalog_variants(
    catalog_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[int, str]]:
    """Load variants from catalogs without mutating originals.

    Returns:
        (all_variants, variant_index_to_catalog_id)
    """
    sb = sb_client
    all_variants: list[dict[str, Any]] = []
    variant_catalog_ids: dict[int, str] = {}

    for cat_id in catalog_ids:
        cat_resp = (
            sb.schema("reverse_search")
            .table("model_document_sources")
            .select("id, extracted_data, display_name")
            .eq("id", cat_id)
            .eq("extraction_status", "ready")
            .limit(1)
            .execute()
        )
        if not cat_resp.data:
            logger.warning("Catalog %s not found or not ready", cat_id)
            continue

        extracted = cat_resp.data[0].get("extracted_data") or {}
        variants = extracted.get("variants", [])
        cat_name = cat_resp.data[0].get("display_name", cat_id)

        for v in variants:
            idx = len(all_variants)
            # Copy variant — never mutate originals
            v_copy = {
                **v,
                "_source_catalog": cat_name,
                "_source_catalog_id": cat_id,
            }
            variant_catalog_ids[idx] = cat_id
            all_variants.append(v_copy)

    return all_variants, variant_catalog_ids


def _perform_matching(
    vehicle_spec: dict[str, Any],
    all_variants: list[dict[str, Any]],
    feature_keys: list[str],
) -> VariantMatchResult | dict[str, Any]:
    """Run exact + LLM matching. Returns result or error dict."""

    exact_variant = find_exact_variant_match(vehicle_spec, all_variants)

    try:
        if exact_variant:
            logger.info(
                "Found EXACT 100%% deterministic match by price: %s",
                exact_variant.get("variant_name"),
            )
            match_result = match_variant_with_llm(
                vehicle_spec, [exact_variant], feature_keys
            )
            match_result.confidence = 1.0
            match_result.reasoning = (
                "Katalog został dopasowany w 100% ze względu na "
                "perfekcyjną zgodność Ceny Bazowej (oraz ew. "
                "nazwy/mocy silnika)."
            )
        else:
            match_result = match_variant_with_llm(
                vehicle_spec, all_variants, feature_keys
            )
    except CrossRefLLMError as exc:
        logger.error("LLM matching infrastructure error: %s", exc)
        return {
            "status": "error",
            "message": f"Błąd infrastruktury LLM: {exc}",
        }

    if match_result.confidence < 0.65:
        return {
            "status": "no_match",
            "message": (
                f"LLM nie znalazł wystarczająco pasującego wariantu "
                f"(Odrzucono. Zaufanie: {match_result.confidence:.2f}. "
                f"Powód: {match_result.reasoning})"
            ),
            "confidence": match_result.confidence,
        }

    return match_result


def _resolve_catalog_id(
    match_result: VariantMatchResult,
    variant_catalog_ids: dict[int, str],
    catalog_ids: list[str],
) -> str:
    """Resolve catalog ID for matched variant."""

    # Fallback to first catalog if we can't determine source
    return catalog_ids[0] if catalog_ids else ""
