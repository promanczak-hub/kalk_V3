"""Vehicle-level CRUD endpoints for feature management.

GET  /vehicles/{id}/features   — read all features for a vehicle
PUT  /vehicles/{id}/features   — batch upsert features
DELETE /vehicles/{id}/features/{feature_key} — remove one feature
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.database import supabase as sb_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Vehicle Features CRUD"])

# ── Models ──────────────────────────────────────────────


class FeatureValuePayload(BaseModel):
    """Single feature update payload."""

    feature_key: str
    value_bool: bool | None = None
    value_num: float | None = None
    value_text: str | None = None
    unit: str | None = None
    display_name: str | None = None
    is_new_manual: bool | None = False


class FeatureBatchUpdate(BaseModel):
    """Batch of features to upsert for a vehicle."""

    features: list[FeatureValuePayload] = Field(default_factory=list)


# ── GET — read all features for a vehicle ────────────────


@router.get("/vehicles/{vehicle_id}/features")
def get_vehicle_features(
    vehicle_id: str,
) -> dict[str, Any]:
    """Return all resolved features for a vehicle.

    Joins vehicle_feature_state with universal_features to provide
    display names, types, and categories.
    """
    sb = sb_client

    state_resp = (
        sb.schema("reverse_search")
        .table("vehicle_feature_state")
        .select(
            "id, feature_id, resolved_status, "
            "resolved_value_bool, resolved_value_num, "
            "resolved_value_text, resolved_unit, "
            "confidence, resolution_source, is_manual_override"
        )
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )
    state_rows: list[dict[str, Any]] = state_resp.data or []

    if not state_rows:
        return {"vehicle_id": vehicle_id, "features": [], "total": 0}

    # Load feature catalog for display names
    feat_resp = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key, display_name, feature_type, category_id")
        .execute()
    )
    feat_map: dict[str, dict[str, Any]] = {f["id"]: f for f in (feat_resp.data or [])}

    # Load categories for grouping
    cat_resp = (
        sb.schema("reverse_search")
        .table("universal_feature_categories")
        .select("id, category_key, display_name")
        .execute()
    )
    cat_map: dict[str, dict[str, str]] = {c["id"]: c for c in (cat_resp.data or [])}

    enriched: list[dict[str, Any]] = []
    for row in state_rows:
        feat_info = feat_map.get(row["feature_id"], {})
        cat_info = cat_map.get(feat_info.get("category_id", ""), {})

        enriched.append(
            {
                "state_id": row["id"],
                "feature_id": row["feature_id"],
                "feature_key": feat_info.get("feature_key", ""),
                "display_name": feat_info.get("display_name", ""),
                "feature_type": feat_info.get("feature_type", ""),
                "category_key": cat_info.get("category_key", ""),
                "category_name": cat_info.get("display_name", ""),
                "resolved_status": row["resolved_status"],
                "value_bool": row["resolved_value_bool"],
                "value_num": row["resolved_value_num"],
                "value_text": row["resolved_value_text"],
                "unit": row["resolved_unit"],
                "confidence": row["confidence"],
                "source": row["resolution_source"],
                "is_manual": row["is_manual_override"],
            }
        )

    # Sort by category then feature name
    enriched.sort(key=lambda x: (x["category_name"], x["display_name"]))

    return {
        "vehicle_id": vehicle_id,
        "features": enriched,
        "total": len(enriched),
    }


# ── PUT — batch upsert features ─────────────────────────


@router.put("/vehicles/{vehicle_id}/features")
def upsert_vehicle_features(
    vehicle_id: str,
    body: FeatureBatchUpdate,
) -> dict[str, Any]:
    """Upsert features for a vehicle.

    Creates or updates vehicle_feature_state entries.
    Uses 'manual_override' source type for manual edits.
    """
    sb = sb_client

    if not body.features:
        raise HTTPException(
            status_code=400,
            detail="No features provided",
        )

    # Load feature catalog to resolve feature_key → feature_id
    feat_resp = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key, feature_type")
        .execute()
    )
    feat_map: dict[str, dict[str, str]] = {
        f["feature_key"]: {"id": f["id"], "type": f["feature_type"]}
        for f in (feat_resp.data or [])
    }

    upserted = 0
    errors: list[str] = []

    for feat in body.features:
        feat_info = feat_map.get(feat.feature_key)
        if not feat_info and feat.is_new_manual and feat.display_name:
            # Utworz nowa cechę uniwersalna w locie (Slugify feature_key and create)
            import re
            
            # Simple slugify
            slug = re.sub(r'[^a-z0-9]+', '_', feat.display_name.lower().strip()).strip('_')
            
            # Wyszukaj kategorie "Inne" (lub ID innej popularnej)
            cat_resp = sb.schema("reverse_search").table("universal_feature_categories").select("id").eq("category_key", "inne").execute()
            cat_id = cat_resp.data[0]["id"] if cat_resp.data else None
            
            new_feat = {
                "category_id": cat_id,
                "feature_key": slug,
                "display_name": feat.display_name,
                "feature_type": "boolean" if feat.value_bool is not None else ("numeric" if feat.value_num is not None else "text"),
                "vehicle_scope": "both",
                "is_active": True,
                "sort_order": 999
            }
            try:
                sb.schema("reverse_search").table("universal_features").upsert(new_feat, on_conflict="feature_key").execute()
                # Reload map for this feature
                new_info_resp = sb.schema("reverse_search").table("universal_features").select("id, feature_type").eq("feature_key", slug).execute()
                if new_info_resp.data:
                    row: dict[str, Any] = new_info_resp.data[0]
                    feat_info = {"id": str(row["id"]), "type": str(row["feature_type"])}
                    feat.feature_key = slug # Zmiana klucza dla dalszego processingu
            except Exception as e:
                errors.append(f"Nie udało się utworzyć cechy {feat.display_name}: {e}")
                continue

        if not feat_info:
            errors.append(f"Unknown feature_key: {feat.feature_key}")
            continue

        state_row: dict[str, Any] = {
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_info["id"],
            "resolved_status": "present_confirmed_primary",
            "confidence": 1.0,
            "resolution_source": "manual_override",
            "is_manual_override": True,
        }

        if feat.value_bool is not None:
            state_row["resolved_value_bool"] = feat.value_bool
        if feat.value_num is not None:
            state_row["resolved_value_num"] = feat.value_num
        if feat.value_text is not None:
            state_row["resolved_value_text"] = feat.value_text
        if feat.unit is not None:
            state_row["resolved_unit"] = feat.unit

        try:
            sb.schema("reverse_search").table("vehicle_feature_state").upsert(
                state_row,
                on_conflict="source_vehicle_id,feature_id",
            ).execute()
            upserted += 1
        except Exception as exc:
            msg = f"Upsert failed for {feat.feature_key}: {exc}"
            errors.append(msg)
            logger.warning(msg)

    return {
        "vehicle_id": vehicle_id,
        "upserted": upserted,
        "errors": errors,
    }


# ── DELETE — remove one feature ──────────────────────────


@router.delete("/vehicles/{vehicle_id}/features/{feature_key}")
def delete_vehicle_feature(
    vehicle_id: str,
    feature_key: str,
) -> dict[str, Any]:
    """Remove a single feature from a vehicle."""
    sb = sb_client

    # Resolve feature_key → feature_id
    feat_resp = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("id")
        .eq("feature_key", feature_key)
        .limit(1)
        .execute()
    )
    rows: list[dict[str, Any]] = feat_resp.data or []
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Feature key not found: {feature_key}",
        )

    feature_id = rows[0]["id"]

    # Delete state
    sb.schema("reverse_search").table("vehicle_feature_state").delete().eq(
        "source_vehicle_id", vehicle_id
    ).eq("feature_id", feature_id).execute()

    # Also delete evidence
    sb.schema("reverse_search").table("vehicle_feature_evidence").delete().eq(
        "source_vehicle_id", vehicle_id
    ).eq("feature_id", feature_id).execute()

    return {
        "deleted": True,
        "vehicle_id": vehicle_id,
        "feature_key": feature_key,
    }
