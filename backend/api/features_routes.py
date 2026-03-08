"""FastAPI routes for the reverse_search / universal features system.

All endpoints under /api/features/...
Isolated from calculator endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.database import supabase

from core.feature_enrichment import enrich_all_vehicles, enrich_vehicle_features
from core.feature_importer import import_features_to_db
from core.feature_resolver import resolve_vehicle_features
from core.models_features import (
    FeatureCatalogResponse,
    FeatureSearchRequest,
    FeatureSearchResponse,
    FeatureSearchResultItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["features"])


# ── Excel Import ───────────────────────────────────────────────


@router.post("/features/import-excel")
async def import_excel_features(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload Excel file and import features into universal_features."""
    if not file.filename or not file.filename.endswith(
        (".xlsx", ".xls"),
    ):
        raise HTTPException(
            status_code=400,
            detail="Plik musi być w formacie .xlsx lub .xls",
        )

    import tempfile
    from pathlib import Path

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".xlsx",
    )
    try:
        contents = await file.read()
        tmp.write(contents)
        tmp.close()

        result = import_features_to_db(
            file_path=tmp.name,
            imported_by="api_upload",
        )
        return {
            "status": "ok",
            "file_name": file.filename,
            **result,
        }
    except Exception as e:
        logger.exception("Excel import failed")
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {e}",
        ) from e
    finally:
        Path(tmp.name).unlink(missing_ok=True)


# ── Feature Catalog ────────────────────────────────────────────


@router.get("/features/catalog")
async def get_feature_catalog() -> FeatureCatalogResponse:
    """List all universal features grouped by category."""
    sb = supabase

    cats_resp = (
        sb.schema("reverse_search")
        .table("universal_feature_categories")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )

    features_resp = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )

    categories: list[dict[str, Any]] = []
    for cat in cats_resp.data:
        cat_features = [f for f in features_resp.data if f["category_id"] == cat["id"]]
        categories.append(
            {
                "id": cat["id"],
                "category_key": cat["category_key"],
                "display_name": cat["display_name"],
                "vehicle_scope": cat["vehicle_scope"],
                "features": cat_features,
            }
        )

    return FeatureCatalogResponse(
        categories=categories,
        total_features=len(features_resp.data),
    )


# ── Vehicle Feature State ─────────────────────────────────────


@router.get("/features/vehicle/{vehicle_id}/state")
async def get_vehicle_feature_state(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get resolved features for a vehicle."""
    sb = supabase

    resp = (
        sb.schema("reverse_search")
        .table("vehicle_features_summary_view")
        .select("*")
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for row in resp.data:
        cat = row.get("category_name", "Inne")
        by_category.setdefault(cat, []).append(row)

    return {
        "vehicle_id": vehicle_id,
        "categories": by_category,
        "total_features": len(resp.data),
    }


# ── Vehicle Feature Evidence ──────────────────────────────────


@router.get("/features/vehicle/{vehicle_id}/evidence")
async def get_vehicle_feature_evidence(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get raw feature evidence for a vehicle."""
    sb = supabase

    resp = (
        sb.schema("reverse_search")
        .table("vehicle_feature_evidence")
        .select("*, universal_features(feature_key, display_name)")
        .eq("source_vehicle_id", vehicle_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "vehicle_id": vehicle_id,
        "evidence": resp.data,
        "total": len(resp.data),
    }


# ── Feature Rebuild ────────────────────────────────────────────


@router.post("/features/vehicle/{vehicle_id}/rebuild")
async def rebuild_vehicle_features(
    vehicle_id: str,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    """Trigger feature state resolution for a vehicle."""
    result = resolve_vehicle_features(vehicle_id, bundle_id)
    return {
        "vehicle_id": vehicle_id,
        "status": "completed",
        **result,
    }


# ── Reverse Search ─────────────────────────────────────────────


@router.post("/features/search")
async def reverse_search_vehicles(
    request: FeatureSearchRequest,
) -> FeatureSearchResponse:
    """Search vehicles by feature criteria.

    Filters on vehicle_feature_state joined with vehicle_synthesis.
    """
    sb = supabase

    if not request.filters:
        raise HTTPException(
            status_code=400,
            detail="At least one filter is required",
        )

    # Build query: find vehicles that match ALL filters
    # Strategy: for each filter, find matching vehicle_ids,
    # then intersect
    matching_sets: list[set[str]] = []

    for flt in request.filters:
        # Find feature_id by feature_key
        feat_resp = (
            sb.schema("reverse_search")
            .table("universal_features")
            .select("id")
            .eq("feature_key", flt.feature_key)
            .limit(1)
            .execute()
        )
        if not feat_resp.data:
            continue

        feature_id = feat_resp.data[0]["id"]

        # Query vehicle_feature_state
        q = (
            sb.schema("reverse_search")
            .table("vehicle_feature_state")
            .select("source_vehicle_id")
            .eq("feature_id", feature_id)
        )

        # Apply value filters
        if flt.value_bool is not None:
            q = q.eq("resolved_value_bool", flt.value_bool)
            q = q.in_(
                "resolved_status",
                [
                    "present_confirmed_primary",
                    "present_confirmed_secondary",
                    "present_inferred",
                ],
            )

        if flt.value_num_min is not None:
            q = q.gte("resolved_value_num", flt.value_num_min)

        if flt.value_num_max is not None:
            q = q.lte("resolved_value_num", flt.value_num_max)

        if flt.value_text is not None:
            q = q.ilike(
                "resolved_value_text",
                f"%{flt.value_text}%",
            )

        state_resp = q.execute()
        vehicle_ids = {r["source_vehicle_id"] for r in state_resp.data}
        matching_sets.append(vehicle_ids)

    if not matching_sets:
        return FeatureSearchResponse(results=[], total_count=0)

    # Intersect all filter results
    result_ids = matching_sets[0]
    for s in matching_sets[1:]:
        result_ids &= s

    if not result_ids:
        return FeatureSearchResponse(results=[], total_count=0)

    # Fetch vehicle info from vehicle_synthesis
    vehicle_ids_list = list(result_ids)[request.offset : request.offset + request.limit]

    vehicles_resp = (
        sb.table("vehicle_synthesis")
        .select("id, brand, model")
        .in_("id", vehicle_ids_list)
        .execute()
    )

    results: list[FeatureSearchResultItem] = []
    for v in vehicles_resp.data:
        results.append(
            FeatureSearchResultItem(
                source_vehicle_id=v["id"],
                brand=v.get("brand"),
                model=v.get("model"),
                matched_features=len(request.filters),
                total_filters=len(request.filters),
                match_score=1.0,
            )
        )

    return FeatureSearchResponse(
        results=results,
        total_count=len(result_ids),
    )


# ── Card Summary Features ─────────────────────────────────────


@router.get("/features/card-summary/{vehicle_id}")
async def get_features_card_summary(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get features formatted for card summary display."""
    sb = supabase

    resp = (
        sb.schema("reverse_search")
        .table("universal_features_card_summary_view")
        .select("*")
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )

    return {
        "vehicle_id": vehicle_id,
        "categories": resp.data,
    }


# ── Brochure Features ─────────────────────────────────────────


@router.get("/features/brochure/{vehicle_id}")
async def get_features_brochure(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get features formatted for brochure."""
    sb = supabase

    resp = (
        sb.schema("reverse_search")
        .table("universal_features_brochure_view")
        .select("*")
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )

    return {
        "vehicle_id": vehicle_id,
        "categories": resp.data,
    }


# ── Feature Enrichment ────────────────────────────────────────


@router.post("/features/vehicle/{vehicle_id}/enrich")
async def enrich_single_vehicle(
    vehicle_id: str,
) -> dict[str, Any]:
    """Enrich a single vehicle with features from card_summary."""
    sb = supabase

    resp = (
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=404,
            detail=f"Vehicle {vehicle_id} not found",
        )

    synthesis = resp.data[0].get("synthesis_data")
    if not isinstance(synthesis, dict):
        raise HTTPException(
            status_code=400,
            detail="Vehicle has no synthesis_data",
        )

    result = enrich_vehicle_features(vehicle_id, synthesis)
    return result


@router.post("/features/enrich-all")
async def enrich_all(
    limit: int = 100,
) -> dict[str, Any]:
    """Batch-enrich all vehicles with features from card_summary."""
    result = enrich_all_vehicles(limit=limit)
    return result
