"""Feature state resolver — merges evidence into vehicle_specs_normalized.

Implements the merge strategy:
1. spec (priority 1)
2. variant_doc (priority 2)
3. catalog (priority 3)
4. brochure (priority 4)
5. price_list (priority 5)
6. excel_import (priority 6)
7. llm_inference (priority 7)

If two sources conflict → contradiction_detected.
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import supabase as sb_client

logger = logging.getLogger(__name__)

_SOURCE_PRIORITY: dict[str, int] = {
    "spec": 1,
    "variant_doc": 2,
    "catalog": 3,
    "brochure": 4,
    "price_list": 5,
    "excel_import": 6,
    "service_option": 6,
    "body_parameters": 6,
    "manual_override": 0,  # highest priority
    "llm_inference": 7,
}

_SOURCE_TO_DOC_TYPE: dict[str, str] = {
    "spec": "config",
    "variant_doc": "config",
    "catalog": "pricelist",
    "brochure": "brochure",
    "price_list": "pricelist",
    "excel_import": "manual",
    "service_option": "config",
    "body_parameters": "config",
    "manual_override": "manual",
    "llm_inference": "llm_inference",
}


def _map_source_to_doc_type(source_type: str) -> str:
    """Map legacy source_type to vehicle_specs_normalized source_document_type."""
    return _SOURCE_TO_DOC_TYPE.get(source_type, "config")


def _resolve_single_feature(
    evidences: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve a single feature from its evidence records.

    Returns a dict suitable for upsert into vehicle_specs_normalized.
    """
    if not evidences:
        return {
            "resolved_status": "unknown",
            "confidence": 0.0,
            "is_manual_override": False,
        }

    # Sort by priority (lower number = higher priority)
    sorted_ev = sorted(
        evidences,
        key=lambda e: _SOURCE_PRIORITY.get(e.get("source_type", ""), 99),
    )

    # Check for manual overrides first
    overrides = [e for e in sorted_ev if e.get("source_type") == "manual_override"]
    if overrides:
        best = overrides[0]
        return _evidence_to_state(best, is_override=True)

    # Check for contradictions (top 2 sources disagree)
    if len(sorted_ev) >= 2:
        top = sorted_ev[0]
        second = sorted_ev[1]
        if _values_conflict(top, second):
            return {
                "resolved_status": "contradiction_detected",
                "value_bool": top.get("value_bool"),
                "value_numeric": top.get("value_num"),
                "value_text": top.get("value_text"),
                "resolved_unit": top.get("unit"),
                "confidence_score": 0.5,
                "source_text": (
                    f"conflict: {top.get('source_type', 'unknown')} vs {second.get('source_type', 'unknown')}"
                ),
                "is_manual_override": False,
                "source_document_type": "config",
            }

    # Use highest priority evidence
    best = sorted_ev[0]
    return _evidence_to_state(best, is_override=False)


def _evidence_to_state(
    evidence: dict[str, Any],
    *,
    is_override: bool,
) -> dict[str, Any]:
    """Convert evidence record to feature state record."""
    source_type = evidence.get("source_type", "unknown")
    ev_status = evidence.get("evidence_status", "observed")

    observed_map: dict[str, str] = {
        "spec": "present_confirmed_primary",
        "variant_doc": "present_confirmed_secondary",
        "catalog": "present_inferred",
        "brochure": "present_inferred",
        "llm_inference": "present_inferred",
    }
    simple_map: dict[str, str] = {
        "inferred": "present_inferred",
        "optional": "optional_package_possible",
        "not_found": "unknown",
        "not_applicable": "not_applicable",
    }

    if ev_status == "observed":
        resolved_status = observed_map.get(
            source_type,
            "present_inferred",
        )
    elif ev_status in simple_map:
        resolved_status = simple_map[ev_status]
    else:
        resolved_status = "unknown"

    if is_override:
        resolved_status = "present_confirmed_primary"

    return {
        "resolved_status": resolved_status,
        "value_bool": evidence.get("value_bool"),
        "value_numeric": evidence.get("value_num"),
        "value_text": evidence.get("value_text"),
        "resolved_unit": evidence.get("unit"),
        "confidence_score": evidence.get("confidence", 0.8),
        "source_document_type": _map_source_to_doc_type(source_type),
        "source_text": evidence.get("source_text"),
        "is_manual_override": is_override,
    }


def _values_conflict(
    ev_a: dict[str, Any],
    ev_b: dict[str, Any],
) -> bool:
    """Check if two evidence records have conflicting values."""
    # Bool conflict
    a_bool = ev_a.get("value_bool")
    b_bool = ev_b.get("value_bool")
    if a_bool is not None and b_bool is not None and a_bool != b_bool:
        return True

    # Numeric conflict (>20% difference)
    a_num = ev_a.get("value_num")
    b_num = ev_b.get("value_num")
    if a_num is not None and b_num is not None:
        if a_num == 0 and b_num == 0:
            return False
        avg = (abs(a_num) + abs(b_num)) / 2
        if avg > 0 and abs(a_num - b_num) / avg > 0.2:
            return True

    # Text conflict — exact mismatch
    a_text = (ev_a.get("value_text") or "").strip().lower()
    b_text = (ev_b.get("value_text") or "").strip().lower()
    if a_text and b_text and a_text != b_text:
        return True

    return False


def resolve_vehicle_features(
    vehicle_id: str,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    """Resolve all features for a vehicle from its evidence.

    Reads vehicle_feature_evidence, resolves conflicts,
    and upserts into vehicle_specs_normalized.

    Returns summary of resolution.
    """
    sb = sb_client

    # Fetch all evidence for this vehicle
    query = (
        sb.schema("reverse_search")
        .table("vehicle_feature_evidence")
        .select("*")
        .eq("source_vehicle_id", vehicle_id)
    )
    if bundle_id:
        query = query.eq("bundle_id", bundle_id)

    ev_resp = query.execute()
    raw_data: list[dict[str, Any]] = ev_resp.data or []  # type: ignore[assignment]
    all_evidence: list[dict[str, Any]] = [dict(row) for row in raw_data]

    if not all_evidence:
        logger.info(
            "No evidence found for vehicle %s",
            vehicle_id,
        )
        return {"resolved": 0, "total_evidence": 0}

    # Group evidence by feature_id
    by_feature: dict[str, list[dict[str, Any]]] = {}
    for ev in all_evidence:
        fid = str(ev["feature_id"])
        by_feature.setdefault(fid, []).append(ev)

    # ── Delete existing state for this vehicle/bundle ──
    del_query = (
        sb.schema("reverse_search")
        .table("vehicle_specs_normalized")
        .delete()
        .eq("vehicle_id", vehicle_id)
    )
    if bundle_id:
        del_query = del_query.eq("source_text", f"bundle:{bundle_id}")
    del_query.execute()

    # ── Build state rows and batch insert ──
    state_rows: list[dict[str, Any]] = []
    for feature_id, evidences in by_feature.items():
        state = _resolve_single_feature(evidences)
        state["vehicle_id"] = vehicle_id
        state["feature_id"] = feature_id
        state_rows.append(state)

    resolved_count = 0
    if state_rows:
        try:
            sb.schema("reverse_search").table(
                "vehicle_specs_normalized",
            ).upsert(
                state_rows,
                on_conflict="vehicle_id,feature_id",
            ).execute()
            resolved_count = len(state_rows)
        except Exception as e:
            logger.error(
                "Failed to insert feature state batch for %s: %s",
                vehicle_id,
                e,
            )

    logger.info(
        "Resolved %d features for vehicle %s from %d evidence records",
        resolved_count,
        vehicle_id,
        len(all_evidence),
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

    # Refresh JSONB Materialized View for fast search
    try:
        sb.rpc(
            "rpc_refresh_vehicle_features",
            {"p_vehicle_id": vehicle_id, "p_bundle_id": bundle_id},
        ).execute()
    except Exception as exc:
        logger.warning(
            "Failed to refresh materialized view for vehicle search: %s", exc
        )

    return {
        "resolved": resolved_count,
        "total_evidence": len(all_evidence),
    }
