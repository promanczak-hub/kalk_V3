"""Evidence creation for cross-referenced features.

Batch-upserts evidence from LLM-matched variants and body params.
"""

from __future__ import annotations

import logging
from typing import Any

from core.body_parameter_calc import calculate_cargo_params
from core.cross_ref_models import VariantMatchResult
from core.database import supabase as sb_client

logger = logging.getLogger(__name__)

# ── Dimension classification config ──────────────────────────────

DIMENSION_ALIASES: dict[str, set[str]] = {
    "length_mm": {
        "dlugosc", "długość", "length", "cargo_length",
    },
    "width_mm": {
        "szerokosc", "szerokość", "width", "cargo_width",
    },
    "height_mm": {
        "wysokosc", "wysokość", "height", "cargo_height",
    },
}

OVERALL_MARKERS: set[str] = {
    "overall", "calkowit", "całkowit", "zewn", "total",
}

MIN_MAPPING_CONFIDENCE = 0.90


def _classify_dimension(key: str) -> tuple[str, bool] | None:
    """Classify a feature key as a dimension.

    Returns:
        (dimension_name, is_overall) or None if not a dimension.
    """
    key_lower = key.lower()
    is_overall = any(m in key_lower for m in OVERALL_MARKERS)
    for dim_name, aliases in DIMENSION_ALIASES.items():
        if any(alias in key_lower for alias in aliases):
            return dim_name, is_overall
    return None


# ── Evidence batch creation ──────────────────────────────────────


def create_evidence_batch(
    vehicle_id: str,
    match_result: VariantMatchResult,
    feature_id_map: dict[str, str],
    source_type: str = "catalog",
) -> int:
    """Create feature evidence records from matched variant.

    Uses batch upsert (single DB call) instead of N+1 pattern.
    """
    evidence_batch: list[dict[str, Any]] = []

    for feat in match_result.features:
        if feat.mapping_confidence < MIN_MAPPING_CONFIDENCE:
            logger.debug(
                "Skipping feature '%s' (confidence: %.2f < %.2f)",
                feat.feature_key,
                feat.mapping_confidence,
                MIN_MAPPING_CONFIDENCE,
            )
            continue

        feat_id = feature_id_map.get(feat.feature_key)
        if not feat_id:
            logger.debug(
                "Feature key '%s' not in catalog, skipping",
                feat.feature_key,
            )
            continue

        evidence: dict[str, Any] = {
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_id,
            "source_type": source_type,
            "evidence_status": "observed",
            "confidence": feat.mapping_confidence,
            "source_text": (
                f"Cross-ref: {match_result.matched_variant_name}"
            ),
        }
        if feat.value_bool is not None:
            evidence["value_bool"] = feat.value_bool
        if feat.value_num is not None:
            evidence["value_num"] = feat.value_num
        if feat.value_text is not None:
            evidence["value_text"] = feat.value_text
        if feat.unit:
            evidence["unit"] = feat.unit

        evidence_batch.append(evidence)

    if not evidence_batch:
        return 0

    try:
        sb_client.schema("reverse_search").table(
            "vehicle_feature_evidence"
        ).upsert(
            evidence_batch,
            on_conflict="source_vehicle_id,feature_id,source_type",
        ).execute()
        return len(evidence_batch)
    except Exception as exc:
        logger.error(
            "Batch evidence upsert failed for vehicle %s: %s",
            vehicle_id,
            exc,
        )
        return 0


# ── Body parameter evidence ─────────────────────────────────────


def _extract_dimensions(
    match_result: VariantMatchResult,
) -> dict[str, float]:
    """Extract cargo/overall dimensions from matched features."""
    dims: dict[str, float] = {}

    for feat in match_result.features:
        if feat.value_num is None:
            continue
        classification = _classify_dimension(feat.feature_key)
        if classification is None:
            continue

        dim_name, is_overall = classification
        key = f"overall_{dim_name}" if is_overall else dim_name
        dims[key] = feat.value_num

    # Fallback: overall → cargo when cargo not available
    for dim in ("length_mm", "width_mm", "height_mm"):
        if dim not in dims and f"overall_{dim}" in dims:
            dims[dim] = dims[f"overall_{dim}"]

    return dims


def create_body_param_evidence(
    vehicle_id: str,
    match_result: VariantMatchResult,
    feature_id_map: dict[str, str],
) -> int:
    """Create body parameter evidence from dimensions.

    Uses batch upsert (single DB call).
    """
    dims = _extract_dimensions(match_result)
    if not dims:
        return 0

    params = calculate_cargo_params(
        cargo_length_mm=dims.get("length_mm"),
        cargo_width_mm=dims.get("width_mm"),
        cargo_height_mm=dims.get("height_mm"),
    )

    calc_features: dict[str, tuple[float | int | None, str]] = {
        "długość_całkowita": (
            dims.get("overall_length_mm"),
            "mm",
        ),
        "szerokość_całkowita": (
            dims.get("overall_width_mm"),
            "mm",
        ),
        "wysokość_całkowita": (
            dims.get("overall_height_mm"),
            "mm",
        ),
        "m2": (params.area_m2, "m²"),
        "ilość_europalet": (params.europallets, "szt"),
        "kubatura_przestrzeni_ładunkowej_w_m3": (
            params.volume_m3,
            "m³",
        ),
    }

    evidence_batch: list[dict[str, Any]] = []
    for feat_key, (value, unit) in calc_features.items():
        if value is None:
            continue
        feat_id = feature_id_map.get(feat_key)
        if not feat_id:
            continue

        evidence_batch.append({
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_id,
            "source_type": "body_parameters",
            "evidence_status": "observed",
            "value_num": float(value),
            "unit": unit,
            "confidence": 0.99,
            "source_text": "Calculated from catalog dimensions",
        })

    if not evidence_batch:
        return 0

    try:
        sb_client.schema("reverse_search").table(
            "vehicle_feature_evidence"
        ).upsert(
            evidence_batch,
            on_conflict="source_vehicle_id,feature_id,source_type",
        ).execute()
        return len(evidence_batch)
    except Exception as exc:
        logger.warning(
            "Body param batch upsert failed for vehicle %s: %s",
            vehicle_id,
            exc,
        )
        return 0


# ── Audit trail ──────────────────────────────────────────────────


def save_catalog_match(
    vehicle_id: str,
    catalog_id: str,
    match_result: VariantMatchResult,
) -> None:
    """Save cross-reference match to audit table."""
    try:
        sb_client.schema("reverse_search").table(
            "vehicle_catalog_matches"
        ).upsert(
            {
                "source_vehicle_id": vehicle_id,
                "catalog_source_id": catalog_id,
                "matched_variant_name": (
                    match_result.matched_variant_name
                ),
                "match_confidence": match_result.confidence,
            },
            on_conflict="source_vehicle_id,catalog_source_id",
        ).execute()
    except Exception as exc:
        logger.warning("Catalog match save error: %s", exc)
