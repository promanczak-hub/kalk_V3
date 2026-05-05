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
        import asyncio
        from core.feature_enrichment import enrich_vehicle_features

        fallback_result = asyncio.run(enrich_vehicle_features(vehicle_id, synthesis))
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


def _vec_to_pg_literal(vec: list[float]) -> str:
    return "[" + ",".join(str(v) for v in vec) + "]"


@celery_app.task
def generate_embedding_for_vehicle(vehicle_id: str) -> dict:
    """Generate semantic + multi-vector embeddings for a vehicle.

    Writes 4 columns: `semantic_embedding` (used by similar_vehicles RPCs and
    `rpc_reverse_search`) and `vector_use_case`/`vector_specs`/`vector_equipment`
    (used by `rpc_search_vehicles_multi_vector`). Each embedding is generated
    independently — partial success still saves what worked.
    """
    logger.info(f"Generating embeddings for vehicle {vehicle_id}")
    sb = supabase
    from core.embeddings import (
        build_equipment_text,
        build_specs_text,
        build_use_case_text,
        build_vehicle_document,
        generate_embedding,
    )

    v_resp = (
        sb.table("vehicle_synthesis")
        .select("brand, model, synthesis_data")
        .eq("id", vehicle_id)
        .execute()
    )
    if not v_resp.data:
        return {"status": "error", "message": "Vehicle not found"}

    row = v_resp.data[0]
    brand = row.get("brand") or ""
    model = row.get("model") or ""
    synthesis = row.get("synthesis_data") or {}

    texts = {
        "semantic_embedding": build_vehicle_document(brand, model, synthesis),
        "vector_use_case": build_use_case_text(brand, model, synthesis),
        "vector_specs": build_specs_text(brand, model, synthesis),
        "vector_equipment": build_equipment_text(brand, model, synthesis),
    }

    update_payload: dict[str, str] = {}
    failures: list[str] = []
    for column, text in texts.items():
        if not text or not text.strip():
            failures.append(f"{column}:empty_text")
            continue
        try:
            vec = generate_embedding(text)
        except Exception as exc:
            logger.exception(f"Embedding error for {vehicle_id} {column}: {exc}")
            failures.append(f"{column}:exception")
            continue
        if not vec:
            failures.append(f"{column}:none")
            continue
        update_payload[column] = _vec_to_pg_literal(vec)

    if not update_payload:
        logger.error(
            f"Failed to generate ANY embedding for vehicle {vehicle_id}: {failures}"
        )
        return {
            "status": "error",
            "message": "All embeddings failed",
            "failures": failures,
        }

    if any(k.startswith("vector_") for k in update_payload):
        update_payload["multi_vectors_at"] = "now()"

    try:
        sb.table("vehicle_synthesis").update(update_payload).eq(
            "id", vehicle_id
        ).execute()
        logger.info(
            f"Saved {sorted(update_payload)} for vehicle {vehicle_id}"
            + (f" (failures: {failures})" if failures else "")
        )
        return {
            "status": "success",
            "vehicle_id": vehicle_id,
            "saved_columns": sorted(update_payload),
            "failures": failures,
        }
    except Exception as e:
        logger.exception(f"DB Error saving embeddings for {vehicle_id}")
        return {"status": "error", "message": str(e)}


@celery_app.task
def backfill_vehicle_embeddings() -> dict:
    """Backfill embeddings for vehicles missing semantic OR any multi-vector column."""
    logger.info("Starting vehicle embedding backfill process")
    sb = supabase

    v_resp = (
        sb.table("vehicle_synthesis")
        .select("id")
        .or_(
            "semantic_embedding.is.null,"
            "vector_use_case.is.null,"
            "vector_specs.is.null,"
            "vector_equipment.is.null"
        )
        .execute()
    )

    vehicles = v_resp.data or []
    logger.info(f"Found {len(vehicles)} vehicles missing one or more embeddings.")

    success_count = 0
    for v in vehicles:
        res = generate_embedding_for_vehicle(v["id"])
        if res.get("status") == "success":
            success_count += 1

    logger.info(
        f"Backfill complete: regenerated {success_count}/{len(vehicles)} vehicles."
    )
    return {
        "status": "success",
        "processed": len(vehicles),
        "successful": success_count,
    }
