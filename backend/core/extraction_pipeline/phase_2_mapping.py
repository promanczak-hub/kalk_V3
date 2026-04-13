import logging
from supabase import Client
from services.ai_mapper_service import map_vehicle_data_flash
from core.engine_mapper import map_to_engine_class
from core.samar_mapper import map_to_samar_class
from core.feature_enrichment import enrich_vehicle_features
from core.feature_cross_reference import rank_catalogs_for_vehicle
from core.redis_cache import cache_invalidate_pattern
from core.extraction_pipeline.utils import (
    update_progress,
    is_cancelled,
    normalize_brand,
)
from tasks.enrichment_tasks import generate_embedding_for_vehicle

logger = logging.getLogger(__name__)


def finalize_vehicle_pipeline(
    supabase: Client,
    vehicle_id: str,
    parsed_data: dict,
    raw_pdf_url: str | None,
    parent_file_id: str,
    document_markdown: str | None = None,
) -> None:
    raw_brand = parsed_data.get("brand")
    if not raw_brand and "metadata" in parsed_data:
        raw_brand = parsed_data["metadata"].get("brand")
    brand = normalize_brand(raw_brand)

    model = parsed_data.get("model")
    if not model and "metadata" in parsed_data:
        model = parsed_data["metadata"].get("model")

    offer_number = parsed_data.get("offer_number")
    if not offer_number and "metadata" in parsed_data:
        offer_number = parsed_data["metadata"].get("offer_number")

    if is_cancelled(parent_file_id, supabase):
        update_progress(supabase, vehicle_id, "cancelled")
        return

    update_progress(supabase, vehicle_id, "mapping_data")
    logger.info(f"[BG TASK] Mapowanie AI (Gemini Flash) dla {vehicle_id}...")
    try:
        mapped_data = map_vehicle_data_flash(parsed_data)

        if not brand or brand == "Brak":
            brand = mapped_data.get("brand", brand)
        if not model or model == "Brak":
            model = mapped_data.get("model", model)

        card_summary = parsed_data.get("card_summary", {})
        trim = mapped_data.get("trim_level")

        # ── 1. Engine mapper (first — doesn't depend on SAMAR) ──
        powertrain = (
            card_summary.get("powertrain", {})
            if isinstance(card_summary.get("powertrain"), dict)
            else {}
        )
        engine_designation = powertrain.get("engine_designation")
        capacity = powertrain.get("engine_capacity")
        power = card_summary.get("power_hp")

        eng_name, eng_cat, eng_candidates = map_to_engine_class(
            fuel=mapped_data.get("fuel"),
            engine_designation=engine_designation,
            power=str(power) if power else None,
            capacity=str(capacity) if capacity else None,
            model=model,
            trim=trim,
        )

        previous_fuel = mapped_data.get("fuel", "")
        is_mhev_previously = "mHEV" in previous_fuel

        if eng_name != "UNKNOWN":
            is_new_mhev = "mHEV" in eng_name
            is_generic_new = eng_name in ["Benzyna (PB)", "Diesel (ON)", "LPG"]
            if is_mhev_previously and is_generic_new and not is_new_mhev:
                logger.info(
                    f"[BG TASK] Guard: Preserving mHEV status '{previous_fuel}' over generic '{eng_name}'"
                )
            else:
                mapped_data["fuel"] = eng_name
                mapped_data["engine_class"] = eng_cat
                mapped_data["engine_candidates"] = eng_candidates
        elif mapped_data.get("fuel"):
            try:
                engines_resp = (
                    supabase.table("engines")
                    .select("category")
                    .eq("name", mapped_data.get("fuel"))
                    .execute()
                )
                if engines_resp.data:
                    mapped_data["engine_class"] = engines_resp.data[0]["category"]
            except Exception as db_e:
                logger.error(
                    f"[BG TASK] Błąd pobierania kategorii silnika fallback: {db_e}"
                )

        # ── 2. SAMAR mapper (last — uses full context incl. seats) ──
        segment = card_summary.get("segment") or card_summary.get("car_segment")
        body_style = card_summary.get("body_style")
        transmission = mapped_data.get("transmission")
        seats_raw = card_summary.get("number_of_seats")

        samar_name, samar_candidates = map_to_samar_class(
            brand=brand,
            model=model,
            segment=segment,
            body_style=body_style,
            trim=trim,
            transmission=transmission,
            number_of_seats=int(seats_raw) if seats_raw else None,
        )
        mapped_data["samar_category"] = samar_name
        mapped_data["samar_candidates"] = samar_candidates

        # ── READINESS CHECK (Soft-Fail dla ręcznej edycji z UI) ──
        if samar_name == "INNE - WYMAGA RĘCZNEGO MAPOWANIA" or not samar_name:
            logger.warning(
                "[BG TASK] Readiness Check (Soft): Brak automatycznie "
                "przypisanej klasy SAMAR dla '%s %s'.",
                brand,
                model,
            )

        if (
            not mapped_data.get("engine_class")
            or mapped_data.get("engine_class") == "UNKNOWN"
        ):
            logger.warning(
                "[BG TASK] Readiness Check (Soft): Brak zidentyfikowanej "
                "klasy silnika dla '%s %s'.",
                brand,
                model,
            )

        # Assign mapped data BEFORE readiness check — ensures data is
        # always persisted to DB regardless of price availability.
        parsed_data["mapped_ai_data"] = mapped_data

    except Exception as map_err:
        logger.error("[BG TASK] Błąd mapowania danych AI: %s", map_err)
        raise

    if is_cancelled(parent_file_id, supabase):
        update_progress(supabase, vehicle_id, "cancelled")
        return

    # ── P0-A: Evaluate price readiness BEFORE DB save ──
    validation_info = card_summary.get("_validation", {})
    parsed_prices = validation_info.get("parsed_prices", {})
    price_is_present = parsed_prices.get("base") is not None

    if price_is_present:
        initial_status = "enriching_features"
    else:
        initial_status = "needs_review"
        logger.warning(
            "[BG TASK] Readiness Check (Soft): Brak ceny bazowej "
            "(base_price) dla '%s %s' (vehicle_id=%s). "
            "Dane zostaną zapisane ze statusem 'needs_review'.",
            brand,
            model,
            vehicle_id,
        )

    # ── P0-A: Partial save — always persist extracted data ──
    update_payload = {
        "brand": brand,
        "model": model,
        "offer_number": offer_number,
        "synthesis_data": parsed_data,
        "verification_status": initial_status,
        "raw_pdf_url": raw_pdf_url,
        "document_category": parsed_data.get("card_summary", {}).get(
            "vehicle_class"
        ),
    }
    if document_markdown is not None:
        update_payload["document_markdown"] = document_markdown

    logger.info(
        "[BG TASK] Zapisuję wyniki do DB dla %s (stan: %s)",
        vehicle_id,
        initial_status,
    )
    supabase.table("vehicle_synthesis").update(update_payload).eq(
        "id", vehicle_id
    ).execute()

    # ── P0-B: If price missing, stop here — data is safe in DB ──
    if not price_is_present:
        logger.warning(
            "[BG TASK] Pipeline zatrzymany na etapie 'needs_review' — "
            "brak ceny bazowej. Dane częściowe (%s %s) zapisano. "
            "Vehicle: %s",
            brand,
            model,
            vehicle_id,
        )
        # Still invalidate caches so the new row appears on frontend
        cache_invalidate_pattern("initial_data")
        cache_invalidate_pattern("filters:*")
        return

    # ── 3. Wzbogacanie cech i ranga katalogu ──
    logger.info("[BG TASK] Szukam dopasowanego katalogu dla auto-enrichmentu...")
    try:
        vehicle_spec = {
            "brand": card_summary.get("brand") or parsed_data.get("brand", ""),
            "model": card_summary.get("model") or parsed_data.get("model", ""),
            "body_style": card_summary.get("body_style", ""),
            "powertrain": card_summary.get("powertrain", ""),
            "power_hp": card_summary.get("power_hp"),
            "drive_type": mapped_data.get("drive_type")
            or card_summary.get("drive_type", ""),
            "transmission": mapped_data.get("gearbox")
            or card_summary.get("transmission", ""),
            "vehicle_class": card_summary.get("vehicle_class", ""),
            "trim_level": card_summary.get("trim_level", ""),
            "base_price": card_summary.get("base_price")
            or parsed_data.get("pricing", {}).get("base_price"),
        }

        if vehicle_spec.get("brand"):
            c_resp = (
                supabase.schema("reverse_search")
                .table("model_document_sources")
                .select("*")
                .eq("extraction_status", "ready")
                .ilike("brand", f"%{vehicle_spec['brand']}%")
                .execute()
            )

            from typing import cast, Any

            catalogs = cast(list[dict[str, Any]], c_resp.data) if c_resp.data else []
            if catalogs:
                ranked = rank_catalogs_for_vehicle(vehicle_spec, catalogs)
                if ranked:
                    best_cat = ranked[0]
                    best_score = best_cat.get("_ranking", {}).get("score", 0.0)

                    if best_score > 0.0:
                        logger.info(
                            f"[BG TASK] Najlepszy katalog: {best_cat['id']} (score: {best_score}). Zapisuję."
                        )
                        current_synth_resp = (
                            supabase.table("vehicle_synthesis")
                            .select("synthesis_data")
                            .eq("id", vehicle_id)
                            .execute()
                        )
                        if current_synth_resp.data:
                            current_synth = (
                                current_synth_resp.data[0].get("synthesis_data") or {}
                            )
                            current_synth["suggested_catalog"] = {
                                "catalog_id": best_cat["id"],
                                "score": best_score,
                                "display_name": best_cat.get(
                                    "display_name", "Nieznany cennik"
                                ),
                            }
                            supabase.table("vehicle_synthesis").update(
                                {"synthesis_data": current_synth}
                            ).eq("id", vehicle_id).execute()
                    else:
                        logger.info(
                            f"[BG TASK] Brak sensownego dopasowania katalogu (szczyt: {best_score})."
                        )
    except Exception as cr_err:
        logger.error(
            f"[BG TASK] Błąd przy próbie zapisania zasugerowanego katalogu: {cr_err}"
        )

    logger.info(
        f"[BG TASK] Uruchamiam standardowe wzbogacanie cech dla {vehicle_id}..."
    )
    try:
        import asyncio

        enrich_result = asyncio.run(enrich_vehicle_features(vehicle_id, parsed_data))
        logger.info(
            f"[BG TASK] Zakończono wzbogacanie. Utworzono {enrich_result.get('evidence_created', 0)} cech."
        )
    except Exception as enrich_err:
        logger.error(f"[BG TASK] Błąd wzbogacania cech dla {vehicle_id}: {enrich_err}")

    # ── 5. Final Completed Status ──
    logger.info(f"[BG TASK] Oznaczam gotowość (stan: completed) dla {vehicle_id}")
    supabase.table("vehicle_synthesis").update({"verification_status": "completed"}).eq(
        "id", vehicle_id
    ).execute()

    try:
        logger.info(
            f"[BG TASK] Kolejkowanie generowania wektorów (Celery) dla {vehicle_id}"
        )
        generate_embedding_for_vehicle.delay(vehicle_id)
    except Exception as emb_e:
        logger.warning(
            f"[BG TASK] Celery niedostępny, generuję embedding synchronicznie: {emb_e}"
        )
        try:
            result = generate_embedding_for_vehicle(vehicle_id)
            logger.info(f"[BG TASK] Embedding synchroniczny: {result.get('status')}")
        except Exception as sync_e:
            logger.error(
                f"[BG TASK] Błąd synchronicznego generowania embeddingu: {sync_e}"
            )

    cache_invalidate_pattern("initial_data")
    cache_invalidate_pattern("filters:*")

    logger.info(f"[BG TASK] Gotowe dla {vehicle_id}")
