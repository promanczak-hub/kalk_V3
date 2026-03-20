import logging
from core.celery_app import celery_app
from core.database import supabase
from core.feature_cross_reference import (
    _build_vehicle_spec,
    _load_catalog_variants,
    _get_feature_keys,
    _get_feature_id_map,
    _resolve_catalog_id,
    find_exact_variant_match,
)
from core.cross_ref_evidence import (
    create_evidence_batch,
    create_body_param_evidence,
    save_catalog_match,
)
from core.cross_ref_llm import match_variant_with_llm
from core.feature_resolver import resolve_vehicle_features

logger = logging.getLogger(__name__)


@celery_app.task
def enrich_vehicle_features_from_catalog(vehicle_id: str) -> dict:
    """Strictly matches vehicle against catalogs in background. Only proceeds on 100% price/code match."""
    logger.info(f"Starting strict background enrichment for {vehicle_id}")
    sb = supabase

    # 1. Fetch vehicle
    v_resp = (
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .limit(1)
        .execute()
    )
    if not v_resp.data:
        return {"status": "error", "message": "Vehicle not found"}

    synthesis = v_resp.data[0].get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary", {})
    vehicle_spec = _build_vehicle_spec(card_summary, synthesis)

    brand = vehicle_spec.get("brand") or ""
    if not brand:
        return {"status": "error", "message": "Vehicle brand is unknown"}

    # 2. Fetch all ready document catalogs for this brand (case insensitive)
    docs_resp = (
        sb.schema("reverse_search")
        .table("model_document_sources")
        .select("id")
        .eq("extraction_status", "ready")
        .ilike("brand", brand)
        .execute()
    )

    catalog_ids = [row["id"] for row in (docs_resp.data or [])]
    if not catalog_ids:
        return {"status": "no_match", "message": "No ready catalogs for this brand"}

    # 3. Load variants
    all_variants, variant_catalog_ids = _load_catalog_variants(catalog_ids)
    if not all_variants:
        return {"status": "no_match", "message": "No variants found in catalogs"}

    # 4. Strict Exact Match only
    exact_variant = find_exact_variant_match(vehicle_spec, all_variants)
    if not exact_variant:
        logger.info(
            f"No 100% exact match found for {vehicle_id}. Falling back to standard LLM enrichment from PDF spec."
        )
        from core.feature_enrichment import enrich_vehicle_features

        fallback_result = enrich_vehicle_features(vehicle_id, synthesis)
        return {"status": "fallback_success", "fallback_result": fallback_result}

    logger.info(
        f"Background enrichment found EXACT match: {exact_variant.get('variant_name')} for {vehicle_id}"
    )

    # 5. Extract features from the exact variant using LLM
    feature_keys = _get_feature_keys()
    feature_id_map = _get_feature_id_map()

    match_result = match_variant_with_llm(vehicle_spec, [exact_variant], feature_keys)
    match_result.confidence = 1.0
    match_result.reasoning = "Automatyczne wzbogacanie w tle (100% match na podstawie Ceny Bazowej i specyfikacji)."

    # 6. Save evidence & resolve
    create_evidence_batch(vehicle_id, match_result, feature_id_map, "catalog")
    create_body_param_evidence(vehicle_id, match_result, feature_id_map)

    matched_cat_id = _resolve_catalog_id(match_result, variant_catalog_ids, catalog_ids)
    if matched_cat_id:
        save_catalog_match(vehicle_id, matched_cat_id, match_result)

    resolve_vehicle_features(vehicle_id)

    logger.info(
        f"Strict background enrichment complete for {vehicle_id}. Extracted {len(match_result.features)} features."
    )

    # Notify frontend of changes via standard mechanism (can just return, frontend can reload on demand or we can send SSE, but for now typical return is fine)

    return {
        "status": "success",
        "matched_variant": match_result.matched_variant_name,
        "features_extracted": len(match_result.features),
    }
