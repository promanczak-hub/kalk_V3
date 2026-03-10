"""FastAPI routes for the reverse_search / universal features system.

All endpoints under /api/features/...
Isolated from calculator endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from pydantic import BaseModel

from core.database import supabase

from core.feature_cross_reference import (
    cross_reference_vehicle,
    wipe_vehicle_features,
)
from core.feature_enrichment import enrich_all_vehicles, enrich_vehicle_features
from core.feature_importer import import_features_to_db
from core.feature_resolver import resolve_vehicle_features
from core.models_features import (
    FeatureCatalogResponse,
    FeatureExtractionRequest,
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
def get_vehicle_feature_state(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get resolved features for a vehicle.

    Lazy enrichment: if no feature state exists yet,
    auto-enrich from vehicle_synthesis.card_summary.
    """
    sb = supabase

    resp = (
        sb.schema("reverse_search")
        .table("vehicle_features_summary_view")
        .select("*")
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )

    # ── Lazy enrichment: auto-populate on first access ──
    if not resp.data:
        logger.info("No feature state for %s — running lazy enrichment", vehicle_id)
        synth_resp = (
            sb.table("vehicle_synthesis")
            .select("id, synthesis_data")
            .eq("id", vehicle_id)
            .limit(1)
            .execute()
        )
        if synth_resp.data:
            synthesis = synth_resp.data[0].get("synthesis_data")
            if isinstance(synthesis, dict):
                enrich_vehicle_features(vehicle_id, synthesis)
                # Re-query after enrichment
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


# ── Feature Wipe ──────────────────────────────────────────────


@router.delete("/features/vehicle/{vehicle_id}/evidence")
async def wipe_vehicle_evidence(
    vehicle_id: str,
    source_type: str | None = None,
) -> dict[str, Any]:
    """Delete all evidence and state for a vehicle.

    Optionally filter by source_type to delete only evidence
    from a specific source (e.g. 'catalog', 'service_option').
    State is always fully wiped for consistency.
    """
    result = wipe_vehicle_features(vehicle_id, source_type)
    return {
        "vehicle_id": vehicle_id,
        "source_type_filter": source_type,
        "status": "wiped",
        **result,
    }


# ── Feature Cross-Reference ───────────────────────────────────


class CrossRefRequest(BaseModel):
    """Request body for cross-reference endpoint."""

    catalog_ids: list[str]


@router.post("/features/vehicle/{vehicle_id}/cross-reference")
async def cross_reference_vehicle_features(
    vehicle_id: str,
    body: CrossRefRequest,
) -> dict[str, Any]:
    """Cross-reference vehicle with selected catalogs.

    Matches vehicle spec against extracted catalog variants via LLM,
    creates evidence records, and resolves feature state.
    """
    if not body.catalog_ids:
        raise HTTPException(
            status_code=400,
            detail="Musisz wybrać przynajmniej jeden katalog",
        )

    result = cross_reference_vehicle(vehicle_id, body.catalog_ids)
    return result


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


# ── Reverse Search AI Extraction ───────────────────────────────


@router.post("/features/extract-text")
async def extract_features_from_text(
    request: FeatureExtractionRequest,
) -> dict[str, Any]:
    """Extract structured feature filters from raw text using LLM."""
    import json
    from google.genai import types
    from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
    from core.reverse_search_llm import (
        REVERSE_SEARCH_SYSTEM_PROMPT,
        ExtractedReverseSearchFeatures,
    )
    from core.models_features import FeatureFilterItem

    if not request.query_text or not request.query_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Tekst do analizy nie może być pusty.",
        )

    client = get_gemini_client()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=request.query_text,
            config=types.GenerateContentConfig(
                system_instruction=REVERSE_SEARCH_SYSTEM_PROMPT,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=ExtractedReverseSearchFeatures,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )
        if not response.text:
            raise ValueError("Pusta odpowiedź od modelu językowego.")

        json_resp = json.loads(response.text)

        # Convert the boolean dictionary into a list of FeatureFilterItem
        filters: list[FeatureFilterItem] = []
        for feature_key, value in json_resp.items():
            if value is True:
                filters.append(
                    FeatureFilterItem(feature_key=feature_key, value_bool=True)
                )

        return {
            "status": "success",
            "extracted_filters": [f.model_dump() for f in filters],
            "total_extracted": len(filters),
        }

    except Exception as e:
        logger.exception(
            "Błąd podczas analizy tekstu przez LLM: %s", getattr(e, "message", str(e))
        )
        raise HTTPException(
            status_code=500,
            detail=f"Analiza tekstu AI nie powiodła się: {e}",
        )


# ── Reverse Search ─────────────────────────────────────────────


@router.post("/features/search")
async def reverse_search_vehicles(
    request: FeatureSearchRequest,
) -> FeatureSearchResponse:
    """Search vehicles by feature criteria.

    Filters on vehicle_feature_state joined with vehicle_synthesis.
    """
    sb = supabase

    if (
        not request.filters
        and not request.body_types
        and request.vehicle_scope == "all"
    ):
        raise HTTPException(
            status_code=400,
            detail="Przynajmniej jeden filtr cechy, typ zabudowy lub kategoria pojazdu jest wymagana",
        )

    # 1. Base Scope and Body Type Filtering (STRICT)
    valid_vehicle_ids: set[str] | None = None

    if request.body_types or (request.vehicle_scope and request.vehicle_scope != "all"):
        bt_resp = sb.table("vehicle_synthesis").select("id, synthesis_data").execute()

        filtered_ids = set()
        for r in bt_resp.data:
            sd = r.get("synthesis_data") or {}
            cs = sd.get("card_summary") or {}
            mapped = sd.get("mapped_ai_data") or {}

            # Scope Check
            scope_matches = True
            if request.vehicle_scope and request.vehicle_scope != "all":
                v_type = str(
                    cs.get("vehicle_type", "")
                    or cs.get("vehicle_class", "")
                    or mapped.get("vehicle_type", "")
                    or mapped.get("vehicle_class", "")
                    or ""
                ).upper()

                if request.vehicle_scope == "commercial":
                    scope_matches = (
                        "DOSTAWCZ" in v_type
                        or "CIĘŻAROW" in v_type
                        or "CIEZAROW" in v_type
                    )
                elif request.vehicle_scope == "passenger":
                    scope_matches = "OSOBOW" in v_type

            # Body Type Check
            body_matches = True
            if request.body_types:
                vals = [
                    str(x).upper()
                    for x in [
                        cs.get("body_style", ""),
                        mapped.get("body_style", ""),
                        sd.get("nadwozie", ""),
                        sd.get("samar_body_type", ""),
                        sd.get("samar_body_style", ""),
                        sd.get("rodzaj_zabudowy", ""),
                    ]
                    if x
                ]

                if not vals:
                    body_matches = False
                else:
                    # Match ANY of the requested body types
                    body_matches = any(
                        any(req_bt.upper() in v for v in vals)
                        for req_bt in request.body_types
                    )

            if scope_matches and body_matches:
                filtered_ids.add(r["id"])

        valid_vehicle_ids = filtered_ids

    # 2. Features Soft Scoring phase
    from collections import defaultdict

    vehicle_feature_hits = defaultdict(int)
    total_requested_features = len(request.filters)

    # If no features are requested but strict filters exist, just pass all strict ones
    if total_requested_features == 0:
        if valid_vehicle_ids is not None:
            for vid in valid_vehicle_ids:
                vehicle_feature_hits[vid] = 0
    else:
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
            for r in state_resp.data:
                vid = r["source_vehicle_id"]
                # Only score if it passes the base valid_vehicle_ids check
                if valid_vehicle_ids is None or vid in valid_vehicle_ids:
                    vehicle_feature_hits[vid] += 1

        # If there are valid body types, but NONE of the features matched, we still want to show them with 0 hits?
        # Typically reverse search returns nothing if literally 0 features matched out of many, but if you want
        # to show 0% matches you can do:
        if valid_vehicle_ids is not None:
            for vid in valid_vehicle_ids:
                if vid not in vehicle_feature_hits:
                    vehicle_feature_hits[vid] = 0

    if not vehicle_feature_hits:
        return FeatureSearchResponse(results=[], total_count=0)

    # Sort vehicle_ids by hits (highest first)
    sorted_vehicle_hits = sorted(
        vehicle_feature_hits.items(), key=lambda x: x[1], reverse=True
    )
    result_ids = {vid for vid, _ in sorted_vehicle_hits}

    # ---------- PHASE 2: Price Calculation & Filtering ----------
    should_calc_price = any(
        [
            request.price_min is not None,
            request.price_max is not None,
        ]
    )

    if should_calc_price:
        from main import CalculatorInput, ControlCenterSettings
        from core.LTRKalkulator import LTRKalkulator

        # 1. Get Control Center settings once
        cc_res = sb.table("control_center").select("*").eq("id", 1).execute()
        if not cc_res.data:
            raise HTTPException(
                status_code=500, detail="Brak ustawień CC dla kalkulatora"
            )

        from typing import cast, Any, Dict

        response_data = cast(Dict[str, Any], cc_res.data[0])
        settings = ControlCenterSettings(**response_data)

        # 2. Extract price ranges and targets
        target_months = request.price_months or 48
        target_mileage = request.price_mileage or 20000
        min_p = request.price_min if request.price_min is not None else 0.0
        max_p = request.price_max if request.price_max is not None else 9999999.0

        # 3. Fetch data for all matched vehicles
        vehicles_data_resp = (
            sb.table("vehicle_synthesis")
            .select("id, brand, model, synthesis_data")
            .in_("id", list(result_ids))
            .execute()
        )

        matching_phase2 = []
        for v in vehicles_data_resp.data:
            synth_data = v.get("synthesis_data") or {}
            card_summary = synth_data.get("card_summary") or {}

            # Base price is required for calc
            base_price_str = card_summary.get("base_price", "0")
            if not base_price_str:
                continue

            try:
                base_price = float(
                    str(base_price_str).replace(" ", "").replace(",", ".")
                )
            except ValueError:
                continue

            if base_price <= 0:
                continue

            calc_input = CalculatorInput(
                vehicle_id=v["id"],
                base_price_net=base_price,
                okres_bazowy=target_months,
                przebieg_bazowy=target_mileage,
                initial_deposit_pct=request.price_deposit_pct or 0.0,
                z_oponami=True,
                replacement_car_enabled=True,
            )

            try:
                engine = LTRKalkulator(input_data=calc_input, settings=settings)
                matrix = engine.build_matrix()

                # Find matching cell
                # We look for the cell where months == target_months and total_km matches roughly target_mileage
                # Since matrix has months and km_per_year
                target_cell = None
                for cell in matrix:
                    if (
                        cell["months"] == target_months
                        and cell["km_per_year"] == target_mileage
                    ):
                        target_cell = cell
                        break

                if target_cell is None:
                    # Try fallback to closest by km_per_year if exact match fails
                    valid_cells = [c for c in matrix if c["months"] == target_months]
                    if valid_cells:
                        target_cell = min(
                            valid_cells,
                            key=lambda c: abs(c["km_per_year"] - target_mileage),
                        )

                if target_cell:
                    pmt = target_cell["price_net"]
                    if min_p <= pmt <= max_p:
                        # Map extra info
                        v["_pmt"] = pmt
                        matching_phase2.append(v)
            except Exception as e:
                import logging

                logging.warning(f"Error calculating PMT for vehicle {v['id']}: {e}")
                continue

        # Update result_ids to only matching
        result_ids = {v["id"] for v in matching_phase2}

        # We also need to map PMT values to results
        pmt_map = {v["id"]: v["_pmt"] for v in matching_phase2}

        # Paginate the restricted set
        vehicle_ids_list = list(result_ids)[
            request.offset : request.offset + request.limit
        ]

        results: list[FeatureSearchResultItem] = []
        for v in matching_phase2:
            if v["id"] in vehicle_ids_list:
                hits = vehicle_feature_hits.get(v["id"], 0)
                score = (
                    hits / total_requested_features
                    if total_requested_features > 0
                    else 1.0
                )
                results.append(
                    FeatureSearchResultItem(
                        source_vehicle_id=v["id"],
                        brand=v.get("brand"),
                        model=v.get("model"),
                        matched_features=hits,
                        total_filters=total_requested_features,
                        match_score=score,
                        price_netto=pmt_map.get(v["id"]),
                    )
                )
    else:
        # Fetch vehicle info from vehicle_synthesis without calculation
        vehicle_ids_list = list(result_ids)[
            request.offset : request.offset + request.limit
        ]

        vehicles_resp = (
            sb.table("vehicle_synthesis")
            .select("id, brand, model")
            .in_("id", vehicle_ids_list)
            .execute()
        )

        results: list[FeatureSearchResultItem] = []
        for v in vehicles_resp.data:
            hits = vehicle_feature_hits.get(v["id"], 0)
            score = (
                hits / total_requested_features if total_requested_features > 0 else 1.0
            )
            results.append(
                FeatureSearchResultItem(
                    source_vehicle_id=v["id"],
                    brand=v.get("brand"),
                    model=v.get("model"),
                    matched_features=hits,
                    total_filters=total_requested_features,
                    match_score=score,
                    price_netto=None,
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
