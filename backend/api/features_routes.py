"""FastAPI routes for the reverse_search / universal features system.

All endpoints under /api/features/...
Isolated from calculator endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel

from core.database import supabase

from core.feature_cross_reference import (
    cross_reference_vehicle,
    wipe_vehicle_features,
)
from core.feature_enrichment import enrich_vehicle_features
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


# ── Feature Catalog ────────────────────────────────────────────


@router.get("/features/catalog")
def get_feature_catalog() -> FeatureCatalogResponse:
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

_TTL_FEATURES_STATE = 180  # 3 minutes — invalidated on resolve/crossref


@router.get("/features/vehicle/{vehicle_id}/state")
def get_vehicle_feature_state(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get resolved features for a vehicle, with Redis cache (TTL 3 min).

    Lazy enrichment: if no feature state exists yet,
    auto-enrich from vehicle_synthesis.card_summary.
    """
    from core.redis_cache import _get_client, _PREFIX
    import json

    client = _get_client()
    cache_key = f"{_PREFIX}features_state:{vehicle_id}"

    if client is not None:
        try:
            cached = client.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: features_state [%s]", vehicle_id)
                return json.loads(cached)
        except Exception as exc:
            logger.debug("Redis GET error [%s]: %s", cache_key, exc)

    sb = supabase
    resp = (
        sb.schema("reverse_search")
        .table("vehicle_features_summary_view")
        .select("*")
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )
    by_category: dict[str, list[dict]] = {}
    for row in resp.data:
        cat = row.get("category_name", "Inne")
        by_category.setdefault(cat, []).append(row)

    result = {
        "vehicle_id": vehicle_id,
        "categories": by_category,
        "total_features": len(resp.data),
    }

    if client is not None:
        try:
            client.setex(
                cache_key, _TTL_FEATURES_STATE, json.dumps(result, default=str)
            )
        except Exception as exc:
            logger.debug("Redis SET error [%s]: %s", cache_key, exc)

    return result


# ── Vehicle Feature Evidence ──────────────────────────────────


@router.get("/features/vehicle/{vehicle_id}/evidence")
def get_vehicle_feature_evidence(
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
def wipe_vehicle_evidence(
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
def cross_reference_vehicle_features(
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
def rebuild_vehicle_features(
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


# ── Catalog Manual Features Selection ──────────────────────────


@router.get("/features/vehicle/{vehicle_id}/catalog-preview")
def preview_catalog_features_endpoint(
    vehicle_id: str,
    catalog_id: str,
) -> dict[str, Any]:
    """Preview features that would be matched from a catalog."""
    from core.feature_cross_reference import preview_catalog_features

    return preview_catalog_features(vehicle_id, catalog_id)


class AddSelectedFeaturesRequest(BaseModel):
    catalog_id: str
    features: list[dict[str, Any]]


@router.post("/features/vehicle/{vehicle_id}/add-selected-catalog-features")
def add_selected_catalog_features(
    vehicle_id: str,
    body: AddSelectedFeaturesRequest,
) -> dict[str, Any]:
    """Add selected features manually from a catalog preview."""
    from core.database import supabase
    from core.feature_resolver import resolve_vehicle_features
    from core.feature_cross_reference import _get_feature_id_map

    feature_id_map = _get_feature_id_map()
    evidence_batch = []

    for feat in body.features:
        feat_key = feat.get("feature_key")
        feat_id = feature_id_map.get(feat_key)
        if not feat_id:
            continue

        evidence: dict[str, Any] = {
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_id,
            "source_type": "manual_override",
            "evidence_status": "observed",
            "confidence": 1.0,
            "source_text": "Ręczny wybór z zasugerowanego cennika",
        }

        if "value_bool" in feat and feat["value_bool"] is not None:
            evidence["value_bool"] = feat["value_bool"]
        if "value_num" in feat and feat["value_num"] is not None:
            evidence["value_num"] = feat["value_num"]
        if "value_text" in feat and feat["value_text"] is not None:
            evidence["value_text"] = feat["value_text"]
        if "unit" in feat and feat["unit"]:
            evidence["unit"] = feat["unit"]

        evidence_batch.append(evidence)

    if evidence_batch:
        try:
            supabase.schema("reverse_search").table("vehicle_feature_evidence").upsert(
                evidence_batch,
                on_conflict="source_vehicle_id,feature_id,source_type",
            ).execute()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Błąd zapisu cech: {exc}")

    # Zapisz w vehicle_catalog_matches fakt, że dopasowaliśmy ręcznie
    try:
        supabase.schema("reverse_search").table("vehicle_catalog_matches").upsert(
            {
                "source_vehicle_id": vehicle_id,
                "catalog_source_id": body.catalog_id,
                "matched_variant_name": "Wybrane ręcznie z cennika",
                "match_confidence": 1.0,
            },
            on_conflict="source_vehicle_id,catalog_source_id",
        ).execute()
    except Exception:
        pass

    # Usuń suggested_catalog bo już dodaliśmy dane
    try:
        current_synth_resp = (
            supabase.table("vehicle_synthesis")
            .select("synthesis_data")
            .eq("id", vehicle_id)
            .execute()
        )
        if current_synth_resp.data:
            current_synth = current_synth_resp.data[0].get("synthesis_data") or {}
            if "suggested_catalog" in current_synth:
                del current_synth["suggested_catalog"]
                supabase.table("vehicle_synthesis").update(
                    {"synthesis_data": current_synth}
                ).eq("id", vehicle_id).execute()
    except Exception:
        pass

    result = resolve_vehicle_features(vehicle_id)
    return {
        "status": "success",
        "added_features": len(evidence_batch),
        "resolve_result": result,
    }


# ── Reverse Search AI Extraction ───────────────────────────────


@router.post("/features/extract-text")
def extract_features_from_text(
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

        # Convert the matched features list into a list of FeatureFilterItem
        filters: list[FeatureFilterItem] = []

        matched_keys = json_resp.get("matched_features", [])
        if not isinstance(matched_keys, list):
            matched_keys = []

        for feature_key in matched_keys:
            if isinstance(feature_key, str) and feature_key.strip():
                filters.append(
                    FeatureFilterItem(feature_key=feature_key.strip(), value_bool=True)
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
def reverse_search_vehicles(
    request: FeatureSearchRequest,
) -> FeatureSearchResponse:
    """Search vehicles by feature criteria.

    Filters on vehicle_feature_state joined with vehicle_synthesis.
    """
    sb = supabase

    if (
        not request.search_query
        and not request.filters
        and not request.body_types
        and request.vehicle_scope == "all"
    ):
        raise HTTPException(
            status_code=400,
            detail="Przynajmniej jeden filtr cechy, wyszukiwanie tekstowe, typ zabudowy lub kategoria pojazdu jest wymagana",
        )

    # 1. Base Scope, Body Type and Free Text Filtering (STRICT)
    valid_vehicle_ids: set[str] | None = None

    if (
        request.search_query
        or request.body_types
        or (request.vehicle_scope and request.vehicle_scope != "all")
    ):
        bt_resp = sb.table("vehicle_synthesis").select("id, synthesis_data").execute()

        filtered_ids = set()
        search_words = (
            [w.lower() for w in request.search_query.split()]
            if request.search_query
            else []
        )

        for r in bt_resp.data:
            sd = r.get("synthesis_data") or {}
            cs = sd.get("card_summary") or {}
            mapped = sd.get("mapped_ai_data") or {}

            # Text Search Check
            word_matches = True
            if search_words:
                # Dump the structure to a lowercased string to find the exact substrings
                import json

                sd_str = json.dumps(sd, ensure_ascii=False).lower()
                for w in search_words:
                    if w not in sd_str:
                        word_matches = False
                        break

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

            if word_matches and scope_matches and body_matches:
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
    # Keep as a list to preserve order
    result_ids_list = [vid for vid, _ in sorted_vehicle_hits]

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
            .in_("id", result_ids_list)
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
                matrix = engine.build_matrix(only_exact=True)

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
                    if request.price_margin_pct is not None:
                        pmt = pmt / (1 - request.price_margin_pct / 100)
                    if min_p <= pmt <= max_p:
                        # Map extra info
                        v["_pmt"] = pmt
                        matching_phase2.append(v)
            except Exception as e:
                import logging

                logging.warning(f"Error calculating PMT for vehicle {v['id']}: {e}")
                continue

        # Update result_ids to only matching, preserving the ordered list!
        matching_phase2_ids = {v["id"] for v in matching_phase2}
        result_ids_list = [vid for vid in result_ids_list if vid in matching_phase2_ids]

        # We also need to map PMT values to results
        pmt_map = {v["id"]: v["_pmt"] for v in matching_phase2}

        # Paginate the restricted set
        vehicle_ids_page = result_ids_list[
            request.offset : request.offset + request.limit
        ]

        results: list[FeatureSearchResultItem] = []
        for v in matching_phase2:
            if v["id"] in vehicle_ids_page:
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
        vehicle_ids_page = result_ids_list[
            request.offset : request.offset + request.limit
        ]

        vehicles_resp = (
            sb.table("vehicle_synthesis")
            .select("id, brand, model")
            .in_("id", vehicle_ids_page)
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

    # Sort the final results to preserve the original hits ordering before returning
    results.sort(key=lambda x: x.matched_features, reverse=True)

    # ---------- PHASE 3: Calculate Facets ----------
    facets: dict[str, int] = {}
    if result_ids_list:
        chunk_size = 150
        for i in range(0, len(result_ids_list), chunk_size):
            chunk = result_ids_list[i : i + chunk_size]

            facet_resp = (
                sb.schema("reverse_search")
                .table("vehicle_feature_state")
                .select("feature_id, universal_features!inner(feature_key)")
                .in_("source_vehicle_id", chunk)
                .eq("resolved_value_bool", True)
                .in_(
                    "resolved_status",
                    [
                        "present_confirmed_primary",
                        "present_confirmed_secondary",
                        "present_inferred",
                    ],
                )
                .execute()
            )

            for r in facet_resp.data:
                uf = r.get("universal_features")
                if uf and isinstance(uf, dict):
                    f_key = uf.get("feature_key")
                    if f_key:
                        facets[f_key] = facets.get(f_key, 0) + 1

    return FeatureSearchResponse(
        results=results,
        total_count=len(result_ids_list),
        facets=facets,
    )


# ── Brochure Features ─────────────────────────────────────────


@router.get("/features/brochure/{vehicle_id}")
def get_features_brochure(
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
def enrich_single_vehicle(
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


@router.post("/features/vehicle/{vehicle_id}/enrich-background")
def enrich_vehicle_background(
    vehicle_id: str,
) -> dict[str, Any]:
    """Trigger background CELERY task to enrich vehicle features from documents."""
    from tasks.enrichment_tasks import enrich_vehicle_features_from_catalog

    task = enrich_vehicle_features_from_catalog.delay(vehicle_id)

    return {"status": "queued", "vehicle_id": vehicle_id, "task_id": task.id}
