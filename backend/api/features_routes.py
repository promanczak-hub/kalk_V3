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
            "extracted_financials": {
                "price_max": json_resp.get("price_max"),
                "duration_months": json_resp.get("duration_months"),
                "annual_mileage": json_resp.get("annual_mileage"),
            },
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

    Filters on vehicle_specs_normalized joined with vehicle_synthesis.
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

    # 1. Base Scope and Body Type Filtering (STRICT) -> returns valid_vehicle_ids
    # Text search is now pushed entirely to the database via p_search_query
    valid_vehicle_ids: list[str] | None = None

    if request.body_types or (request.vehicle_scope and request.vehicle_scope != "all"):
        all_synthesis_data = []
        page_size = 900
        offset = 0
        while True:
            bt_resp = (
                sb.table("vehicle_synthesis")
                .select("id, synthesis_data")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            data = bt_resp.data or []
            all_synthesis_data.extend(data)
            if len(data) < page_size:
                break
            offset += page_size

        filtered_ids = set()

        for r in all_synthesis_data:
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
                    body_matches = any(
                        any(req_bt.upper() in v for v in vals)
                        for req_bt in request.body_types
                    )

            if scope_matches and body_matches:
                filtered_ids.add(r["id"])

        valid_vehicle_ids = list(filtered_ids)
        if not valid_vehicle_ids:
            return FeatureSearchResponse(results=[], total_count=0, facets={})

    # 2. Map frontend filters to p_requirements JSON
    p_reqs: list[dict[str, Any]] = []

    if request.filters:
        for flt in request.filters:
            # By default eq constraint
            op = "eq"
            val: Any = None
            if flt.value_bool is not None:
                op = "eq"
                val = str(flt.value_bool).lower()  # true/false string
            elif flt.value_text is not None:
                op = "ilike"  # use ilike for text if possible, or eq
                val = flt.value_text
            elif flt.value_num_min is not None and flt.value_num_max is not None:
                # the RPC handles min/max separately by operator if mapped as two items
                p_reqs.append(
                    {
                        "feature_key": flt.feature_key,
                        "operator": "gte",
                        "value": str(flt.value_num_min),
                        "weight": 1.0,
                        "requirement": "NICE_TO_HAVE",
                    }
                )
                p_reqs.append(
                    {
                        "feature_key": flt.feature_key,
                        "operator": "lte",
                        "value": str(flt.value_num_max),
                        "weight": 1.0,
                        "requirement": "NICE_TO_HAVE",
                    }
                )
                continue
            elif flt.value_num_min is not None:
                op = "gte"
                val = str(flt.value_num_min)
            elif flt.value_num_max is not None:
                op = "lte"
                val = str(flt.value_num_max)

            if val is not None:
                p_reqs.append(
                    {
                        "feature_key": flt.feature_key,
                        "operator": op,
                        "value": val,
                        "weight": 1.0,
                        "requirement": "NICE_TO_HAVE",
                    }
                )

    # 3. Add Pricing / Margin requirements
    if request.price_months is not None:
        p_reqs.append(
            {
                "feature_key": "duration_months",
                "operator": "eq",
                "value": str(request.price_months),
                "weight": 0,
            }
        )
    if request.price_mileage is not None:
        p_reqs.append(
            {
                "feature_key": "annual_mileage",
                "operator": "eq",
                "value": str(request.price_mileage),
                "weight": 0,
            }
        )
    if request.price_margin_pct is not None and request.price_margin_pct != "":
        p_reqs.append(
            {
                "feature_key": "margin_pct",
                "operator": "eq",
                "value": str(request.price_margin_pct),
                "weight": 0,
            }
        )

    # Ensure price limits are passed to filter in RPC
    if request.price_min is not None and request.price_min != "":
        p_reqs.append(
            {
                "feature_key": "monthly_price_net",
                "operator": "gte",
                "value": str(request.price_min),
                "weight": 1.0,
            }
        )
    if request.price_max is not None and request.price_max != "":
        p_reqs.append(
            {
                "feature_key": "monthly_price_net",
                "operator": "lte",
                "value": str(request.price_max),
                "weight": 1.0,
            }
        )

    # 4. Call rpc_reverse_search via HTTP to specify the schema
    rpc_payload = {
        "p_requirements": p_reqs,
    }
    if request.search_query:
        rpc_payload["p_search_query"] = request.search_query

        # Generation of semantic vector for Hybrid Search
        try:
            from core.embeddings import generate_embedding

            query_vector = generate_embedding(request.search_query)
            if query_vector:
                rpc_payload["p_semantic_query_vector"] = (
                    f"[{','.join(str(v) for v in query_vector)}]"
                )
        except Exception as e:
            logger.warning(
                f"Semantic Search Error: Failed to generate query vector: {e}"
            )

    if valid_vehicle_ids is not None:
        rpc_payload["p_vehicle_ids"] = valid_vehicle_ids

    import httpx

    # We must call the reverse_search schema explicitly because supabase-py defaults to public for RPCs
    response = httpx.post(
        f"{sb.supabase_url}/rest/v1/rpc/rpc_reverse_search",
        headers={
            "apikey": sb.supabase_key,
            "Authorization": f"Bearer {sb.supabase_key}",
            "Accept-Profile": "reverse_search",
            "Content-Profile": "reverse_search",
        },
        json=rpc_payload,
        timeout=30.0,
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"RPC Error: {response.text}")

    rpc_data = response.json() or []

    total_requested_features = len(request.filters) if request.filters else 0

    results: list[FeatureSearchResultItem] = []

    # Map RPC output to FeatureSearchResultItem
    # rpc_reverse_search returns top 200, we apply pagination limit/offset here
    paginated_data = rpc_data[request.offset : request.offset + request.limit]

    for row in paginated_data:
        matched_features = row.get("matched_features", [])
        score = (
            row.get("match_score_pct", 0) / 100.0 if row.get("match_score_pct") else 0
        )

        results.append(
            FeatureSearchResultItem(
                source_vehicle_id=row["vehicle_id"],
                brand=row["brand"],
                model=row["model"],
                matched_features=len(matched_features),
                total_filters=total_requested_features,
                match_score=score,
                price_netto=row.get("best_monthly_price"),
            )
        )

    # 5. Calculate Facets from the first 150 IDs for speed
    facets: dict[str, int] = {}
    result_ids_list = [r["vehicle_id"] for r in rpc_data]

    if result_ids_list:
        chunk = result_ids_list[:150]
        facet_resp = (
            sb.schema("reverse_search")
            .table("vehicle_specs_normalized")
            .select("feature_id, universal_features!inner(feature_key)")
            .in_("vehicle_id", chunk)
            .eq("value_bool", True)
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
        total_count=len(rpc_data),
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
