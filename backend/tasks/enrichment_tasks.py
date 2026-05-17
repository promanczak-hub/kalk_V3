import logging
from datetime import datetime, timedelta, timezone

from celery.exceptions import Reject
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

# Redis SET trackujący pojazdy z nieudanym embeddingiem — zapełniany przez
# phase_2 trigger (jako fallback gdy Celery .delay padnie) i czyszczony po
# sukcesie w generate_embedding_for_vehicle. backfill_recent_vehicle_embeddings
# odczytuje ten set jako fast-lane priority.
PENDING_EMBEDDING_SET = "kalk_v3:embedding:pending"


def _redis_srem_pending(vehicle_id: str) -> None:
    """Best-effort cleanup po sukcesie embeddingu. Nigdy nie rzuca."""
    try:
        from core.redis_cache import _get_client

        client = _get_client()
        if client is not None:
            client.srem(PENDING_EMBEDDING_SET, vehicle_id)
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.debug(f"Redis SREM pending failed for {vehicle_id}: {exc}")


def _redis_smembers_pending() -> list[str]:
    """Best-effort fetch listy oczekujących pojazdów. Zwraca [] gdy Redis down."""
    try:
        from core.redis_cache import _get_client

        client = _get_client()
        if client is None:
            return []
        members = client.smembers(PENDING_EMBEDDING_SET)
        return [m for m in members] if members else []
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Redis SMEMBERS pending failed: {exc}")
        return []


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


_EMBEDDING_COLUMNS = (
    "semantic_embedding",
    "vector_use_case",
    "vector_specs",
    "vector_equipment",
)


def _do_generate_embeddings(vehicle_id: str) -> dict:
    """Czysta funkcja generująca embeddingi dla pojazdu.

    Idempotentna: regeneruje TYLKO kolumny aktualnie NULL w DB. Wywoływana
    z taska Celery (z retry/backoff) i z backfilli (bez retry — niech kolejny
    cykl spróbuje ponownie).

    Może rzucić wyjątek (np. transient API/SSL/network) — caller decyduje
    czy retry. Rzuca :class:`celery.exceptions.Reject` na terminalne błędy
    (vehicle not found, wszystkie teksty puste), żeby autoretry ich nie łapał.
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

    # 1. Pobierz pojazd + sprawdź które kolumny już są wypełnione
    select_cols = "brand, model, synthesis_data, " + ", ".join(_EMBEDDING_COLUMNS)
    v_resp = (
        sb.table("vehicle_synthesis")
        .select(select_cols)
        .eq("id", vehicle_id)
        .execute()
    )
    if not v_resp.data:
        # Terminal — pojazd nie istnieje, retry niczego nie zmieni.
        raise Reject(reason=f"Vehicle {vehicle_id} not found", requeue=False)

    row = v_resp.data[0]
    brand = row.get("brand") or ""
    model = row.get("model") or ""
    synthesis = row.get("synthesis_data") or {}

    # Idempotency: jeśli wszystkie 4 kolumny już są — nic nie rób.
    already_present = {col for col in _EMBEDDING_COLUMNS if row.get(col) is not None}
    if len(already_present) == len(_EMBEDDING_COLUMNS):
        logger.info(f"Vehicle {vehicle_id} already has all embeddings — skipping")
        _redis_srem_pending(vehicle_id)
        return {
            "status": "success",
            "vehicle_id": vehicle_id,
            "skipped": True,
            "saved_columns": [],
            "failures": [],
        }

    # 2. Buduj teksty TYLKO dla brakujących kolumn
    text_builders = {
        "semantic_embedding": lambda: build_vehicle_document(brand, model, synthesis),
        "vector_use_case": lambda: build_use_case_text(brand, model, synthesis),
        "vector_specs": lambda: build_specs_text(brand, model, synthesis),
        "vector_equipment": lambda: build_equipment_text(brand, model, synthesis),
    }
    texts = {
        col: text_builders[col]()
        for col in _EMBEDDING_COLUMNS
        if col not in already_present
    }

    # 3. Generuj embeddingi per kolumna (partial success allowed)
    update_payload: dict[str, str] = {}
    failures: list[str] = []
    transient_errors: list[Exception] = []
    for column, text in texts.items():
        if not text or not text.strip():
            failures.append(f"{column}:empty_text")
            continue
        try:
            vec = generate_embedding(text)
        except Exception as exc:
            # Transient (Vertex 429, network, SSL/EOF) — zachowujemy i ewentualnie
            # rzucamy na końcu, żeby Celery zrobił autoretry.
            logger.warning(
                f"Embedding error for {vehicle_id} {column}: {exc!r}"
            )
            failures.append(f"{column}:exception:{type(exc).__name__}")
            transient_errors.append(exc)
            continue
        if not vec:
            failures.append(f"{column}:none")
            continue
        update_payload[column] = _vec_to_pg_literal(vec)

    # 4. Wszystkie teksty były puste → terminal (Reject, bez retry)
    if not update_payload and not transient_errors:
        all_empty = all(f.endswith(":empty_text") or f.endswith(":none") for f in failures)
        if all_empty:
            logger.error(
                f"All texts empty for vehicle {vehicle_id}: {failures} — terminal"
            )
            raise Reject(
                reason=f"All embedding texts empty for {vehicle_id}",
                requeue=False,
            )

    # 5. Zapisz to co się udało wygenerować
    if update_payload:
        if any(k.startswith("vector_") for k in update_payload):
            update_payload["multi_vectors_at"] = "now()"
        sb.table("vehicle_synthesis").update(update_payload).eq(
            "id", vehicle_id
        ).execute()
        logger.info(
            f"Saved {sorted(update_payload)} for vehicle {vehicle_id}"
            + (f" (failures: {failures})" if failures else "")
        )

    # 6. Jeśli były transient errors a my mamy jeszcze brakujące kolumny —
    # rzucamy je, niech Celery zrobi retry z backoffem.
    still_missing = set(_EMBEDDING_COLUMNS) - already_present - set(update_payload.keys())
    if still_missing and transient_errors:
        # Wybierz pierwszy najbardziej "ciekawy" błąd jako reason — Celery
        # autoretry_for=(Exception,) złapie i zaplanuje retry.
        raise transient_errors[0]

    # 7. Sukces (pełny lub częściowy, ale bez retryowalnych błędów)
    if not still_missing:
        _redis_srem_pending(vehicle_id)

    return {
        "status": "success",
        "vehicle_id": vehicle_id,
        "saved_columns": sorted(c for c in update_payload if c != "multi_vectors_at"),
        "failures": failures,
        "still_missing": sorted(still_missing),
    }


@celery_app.task(
    bind=True,
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def generate_embedding_for_vehicle(self, vehicle_id: str) -> dict:
    """Generate semantic + multi-vector embeddings for a vehicle.

    Writes 4 columns: `semantic_embedding` (used by similar_vehicles RPCs and
    `rpc_reverse_search`) and `vector_use_case`/`vector_specs`/`vector_equipment`
    (used by `rpc_search_vehicles_multi_vector`). Each embedding is generated
    independently — partial success still saves what worked.

    Retry: do 5 prób z exponential backoff + jitter (do 600s cap). Terminal
    failures (`Vehicle not found`, all texts empty) rzucają `Reject(requeue=False)`
    — nie są retry'owane. Sukces best-effort SREM z `kalk_v3:embedding:pending`.
    """
    logger.info(
        f"embedding_task_attempt vehicle={vehicle_id} attempt={self.request.retries + 1}/{self.max_retries + 1}"
    )
    return _do_generate_embeddings(vehicle_id)


@celery_app.task
def backfill_vehicle_embeddings() -> dict:
    """Defensive full-sweep backfill: regeneruje embeddingi dla wszystkich
    pojazdów z NULL w jakiejkolwiek z 4 kolumn wektorowych. Odpalany co 6h
    przez beat schedule. Wewnątrz wywołuje `_do_generate_embeddings` bez
    retry — kolejny sweep złapie ewentualne porażki."""
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
        try:
            res = _do_generate_embeddings(v["id"])
        except Reject as exc:
            logger.warning(f"Backfill rejected {v['id']}: {exc.reason}")
            continue
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Backfill failed for {v['id']}: {exc}")
            continue
        if res.get("status") == "success" and not res.get("still_missing"):
            success_count += 1

    logger.info(
        f"Backfill complete: regenerated {success_count}/{len(vehicles)} vehicles."
    )
    return {
        "status": "success",
        "processed": len(vehicles),
        "successful": success_count,
    }


@celery_app.task
def backfill_recent_vehicle_embeddings() -> dict:
    """Fast-lane backfill (co 10 min) dla pojazdów świeżo wyekstrahowanych
    LUB explicite zarejestrowanych w Redis SET `kalk_v3:embedding:pending`.

    Skraca worst-case okno "świeży pojazd bez embeddingów → 'Brak podobnych'"
    z 6h (defensive sweep) na <10 min. Nie hammeruje Vertex AI pełnym
    katalogiem co 10 min — tylko ostatnie 2h + jawnie pending.
    """
    logger.info("Starting recent-vehicle embedding backfill process")
    sb = supabase

    # Recent vehicles (2h window) z jakimkolwiek NULL.
    # NB: PostgREST nie ewaluuje SQL — przekazujemy gotowy ISO timestamp
    # liczony po stronie Pythona zamiast `now() - interval '2 hours'`.
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    recent_resp = (
        sb.table("vehicle_synthesis")
        .select("id, created_at")
        .or_(
            "semantic_embedding.is.null,"
            "vector_use_case.is.null,"
            "vector_specs.is.null,"
            "vector_equipment.is.null"
        )
        .gte("created_at", two_hours_ago)
        .execute()
    )
    recent_ids = [v["id"] for v in (recent_resp.data or [])]

    # Plus pending z Redis (best-effort, [] gdy down)
    pending_ids = _redis_smembers_pending()

    # Unique union
    all_ids = list({*recent_ids, *pending_ids})
    logger.info(
        f"Recent backfill: {len(recent_ids)} recent + {len(pending_ids)} pending = {len(all_ids)} unique"
    )

    success_count = 0
    for vid in all_ids:
        try:
            res = _do_generate_embeddings(vid)
        except Reject as exc:
            logger.warning(f"Recent backfill rejected {vid}: {exc.reason}")
            continue
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Recent backfill failed for {vid}: {exc}")
            continue
        if res.get("status") == "success" and not res.get("still_missing"):
            success_count += 1

    logger.info(
        f"Recent backfill complete: {success_count}/{len(all_ids)} vehicles."
    )
    return {
        "status": "success",
        "processed": len(all_ids),
        "successful": success_count,
        "recent": len(recent_ids),
        "pending": len(pending_ids),
    }
