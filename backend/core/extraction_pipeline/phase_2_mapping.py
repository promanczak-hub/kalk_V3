import logging
import re

from supabase import Client
from services.ai_mapper_service import map_vehicle_data_flash
from core.engine_mapper import map_to_engine_class
from core.extractor_models import TransmissionTyp
from core.samar_mapper import map_to_samar_class
from core.feature_enrichment import enrich_vehicle_features
from core.feature_cross_reference import rank_catalogs_for_vehicle
from core.redis_cache import cache_invalidate_pattern
from core.extraction_pipeline.utils import (
    update_progress,
    is_cancelled,
    normalize_brand,
)
from core.model_normalizer import normalize_model_trim_body
from core.composite_body_style import compose_body_style
from tasks.enrichment_tasks import generate_embedding_for_vehicle

logger = logging.getLogger(__name__)


_AUTOMATIC_KEYWORDS = ("automat", "dsg", "tronic", "cvt", "edc", "powershift", "multitronic", "pdk")
_MANUAL_KEYWORDS = ("manual", "ręczna", "reczna")

_MHEV_RE = re.compile(r"\b(m-?HEV|miękka\s+hybryd)", re.IGNORECASE)
_PB_HINTS = ("benzyn", "pb", "tsi", "tfsi", "thp", "puretech", "ecoboost")
_ON_HINTS = ("diesel", " on", "tdi", "hdi", "bluehdi", "dci", "cdi", "jtd")


# ── HITL trigger heuristics ──

_HITL_CONFIDENCE_THRESHOLD = 0.7
_HITL_BLOCKING_RULES = frozenset(
    {
        "BASE_TOTAL_SWAPPED",
        "TOTAL_BELOW_BASE",
        "OPTION_PRICE_UNPARSEABLE",
        "DEALER_EXTRA_NOT_IN_NON_DISCOUNTABLE",
        "BASE_PLUS_OPTIONS_VS_TOTAL",
        "SERVICE_EQUIPMENT_SUM_MISMATCH",
        "FULL_SUM_INTEGRITY",
        "PRICE_DOMAIN_UNKNOWN",
        # V3 (added 2026-05-19) — net/gross/vat triangulation conflict.
        "VAT_TRIANGULATION_FAILED",
    }
)

# V3 rules that OPEN the HITL wizard but do NOT block pipeline continuation.
# Severity is typically INFO or WARNING. User reviews in wizard at their
# leisure — ekstrakcja idzie do bazy.
_HITL_RECOMMENDED_RULES = frozenset(
    {
        "CANONICAL_DUPLICATE_DETECTED",       # dedup signal — user picks which copy stays
        "MULTI_VEHICLE_TWIN_INCOMPLETE",      # one twin missing base_price
        "VAT_RATE_NON_STANDARD",              # non-{0/0.05/0.08/0.23} — may be legit
    }
)


def _needs_hitl_review(card_summary: dict) -> tuple[bool, list[str]]:
    """Decyduje czy ekstrakcja wymaga ręcznego review (HITL wizard).

    Zwraca (needs_review: bool, reasons: list[str]) — reasons wprost wskazują
    pola/reguły które spowodowały wymóg review.
    """
    if not isinstance(card_summary, dict):
        return False, []

    reasons: list[str] = []

    # 1. Halucynacje — twardy trigger
    hallucinated = card_summary.get("hallucinated_fields") or []
    if hallucinated:
        reasons.append(f"hallucinated_fields={hallucinated}")

    # 2. Pole z confidence < threshold w confidence_breakdown
    breakdown = card_summary.get("confidence_breakdown") or {}
    for key, conf in breakdown.items():
        if isinstance(conf, (int, float)) and conf < _HITL_CONFIDENCE_THRESHOLD:
            reasons.append(f"low_confidence:{key}={conf:.2f}")

    # 3. paid_options / service_equipment.components z confidence < threshold
    for idx, opt in enumerate(card_summary.get("paid_options") or []):
        if isinstance(opt, dict):
            conf = opt.get("confidence", 1.0)
            if isinstance(conf, (int, float)) and conf < _HITL_CONFIDENCE_THRESHOLD:
                reasons.append(f"low_confidence:paid_options[{idx}]={conf:.2f}")

    se = card_summary.get("service_equipment") or {}
    for idx, comp in enumerate(se.get("components", []) if isinstance(se, dict) else []):
        if isinstance(comp, dict):
            conf = comp.get("confidence", 1.0)
            if isinstance(conf, (int, float)) and conf < _HITL_CONFIDENCE_THRESHOLD:
                reasons.append(f"low_confidence:service_equipment.components[{idx}]={conf:.2f}")

    # 4. Validator z blocking / recommended severity / rule
    validation = card_summary.get("_validation") or {}
    for warn in validation.get("warnings") or []:
        if not isinstance(warn, dict):
            continue
        rule = warn.get("rule", "")
        severity = warn.get("severity", "")
        if severity == "ERROR" or rule in _HITL_BLOCKING_RULES:
            reasons.append(f"validator:{rule}({severity})")
        elif rule in _HITL_RECOMMENDED_RULES:
            reasons.append(f"validator_recommended:{rule}({severity})")

    # 5. Legacy: _requires_user_input (np. brak base_price)
    if card_summary.get("_requires_user_input"):
        reasons.append(f"requires_user_input={card_summary['_requires_user_input']}")

    return (len(reasons) > 0, reasons)


def detect_mhev_fuel_override(
    parsed_data: dict,
    card_summary: dict,
    mapped_fuel: str | None,
    document_markdown: str | None = None,
) -> str | None:
    """Return the canonical mHEV fuel name when the PDF contains an m-HEV signal.

    Gemini Pro occasionally drops the m-HEV / mHEV / "miękka hybryda" marker from
    `card_summary.fuel` even when the source PDF explicitly states it. Without this
    guard the downstream AI mapper falls through to plain `Benzyna (PB)` /
    `Diesel (ON)`, which selects the wrong row in the `engines` table and breaks
    the WR cascade for non-baseline periods.

    Three signal tiers, in priority order:
      1. Raw `document_markdown` (PDF text as extracted by PyMuPDF) — strongest,
         survives Gemini Pro's field-by-field re-encoding.
      2. card_summary fields (powertrain, engine_designation, engine_marketing_name,
         fuel) — Gemini-mapped, may have dropped the marker.
      3. parsed_data top-level (engine_designation, fuel).
    """
    search_fields: list = []
    pt = card_summary.get("powertrain")
    if isinstance(pt, str):
        search_fields.append(pt)
    elif isinstance(pt, dict):
        search_fields.extend(str(v) for v in pt.values() if v)
    for key in ("engine_designation", "engine_marketing_name", "fuel"):
        v = card_summary.get(key)
        if v:
            search_fields.append(str(v))
    for key in ("engine_designation", "fuel"):
        v = parsed_data.get(key)
        if v:
            search_fields.append(str(v))

    has_signal = any(_MHEV_RE.search(s) for s in search_fields if s)
    md_signal = bool(document_markdown and _MHEV_RE.search(document_markdown))
    if not has_signal and not md_signal:
        return None

    base = (mapped_fuel or "").lower()
    blob = " ".join(s.lower() for s in search_fields)
    md_blob = (document_markdown or "").lower()
    if (
        any(h in base for h in _PB_HINTS)
        or any(h in blob for h in _PB_HINTS)
        or any(h in md_blob for h in _PB_HINTS)
    ):
        return "Benzyna mHEV (PB-mHEV)"
    if (
        any(h in base for h in _ON_HINTS)
        or any(h in blob for h in _ON_HINTS)
        or any(h in md_blob for h in _ON_HINTS)
    ):
        return "Diesel mHEV (ON-mHEV)"
    return "Benzyna mHEV (PB-mHEV)"


def normalize_transmission(raw: str | None) -> str | None:
    """Mapuje surowy tekst skrzyni biegów (np. '6-biegowa manualna', 'DSG7') do
    znormalizowanej wartości ze słownika `transmission_types` (Manualna /
    Automatyczna). Zwraca None gdy nie da się jednoznacznie sklasyfikować."""
    if not raw:
        return None
    text = raw.strip().lower()
    if not text or text in {"brak", "-"}:
        return None
    if any(kw in text for kw in _AUTOMATIC_KEYWORDS):
        return TransmissionTyp.AUTOMATYCZNA.value
    if any(kw in text for kw in _MANUAL_KEYWORDS):
        return TransmissionTyp.MANUALNA.value
    return None


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

        # m-HEV pre-flight: rescue the marker when AI mapper dropped it.
        # When present, this seeds the guard at the foot of the block so a
        # subsequent generic engine_mapper result can't override it.
        # Includes raw document_markdown scan — Gemini Pro can drop m-HEV from
        # structured fields even when the PDF text clearly contains it.
        mhev_override = detect_mhev_fuel_override(
            parsed_data, card_summary, mapped_data.get("fuel"), document_markdown
        )
        if mhev_override and mapped_data.get("fuel") != mhev_override:
            logger.info(
                "[BG TASK] m-HEV detected in extraction text — fuel upgrade "
                f"'{mapped_data.get('fuel')}' -> '{mhev_override}'"
            )
            mapped_data["fuel"] = mhev_override

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

        # Normalize transmission to SOT enum (Manualna / Automatyczna).
        # Source priority: AI-mapped value (already cleaned) → raw OCR text.
        normalized_transmission = (
            normalize_transmission(mapped_data.get("transmission"))
            or normalize_transmission(card_summary.get("transmission"))
        )
        if normalized_transmission:
            mapped_data["transmission_type"] = normalized_transmission

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

        # Czysty engine_type_id z mappera LLM (+ reguła „LPG wygrywa") — kalkulacja
        # czyta to zamiast zgadywać heurystyką z free-textu engine_category.
        # Fail-soft: gdy się nie uda, zostaw bez id (calc ma własny fallback).
        try:
            from core.ltr_vehicle_resolvers import resolve_engine_type_id

            mapped_data["engine_type_id"] = resolve_engine_type_id(
                mapped_data.get("fuel"),
                card_summary.get("fuel"),
                card_summary.get("engine_category"),
            )
        except Exception as eng_err:
            logger.info("[BG TASK] Nie zapisano engine_type_id: %s", eng_err)

        # Assign mapped data BEFORE readiness check — ensures data is
        # always persisted to DB regardless of price availability.
        parsed_data["mapped_ai_data"] = mapped_data

    except Exception as map_err:
        logger.error("[BG TASK] Błąd mapowania danych AI: %s", map_err)
        raise

    if is_cancelled(parent_file_id, supabase):
        update_progress(supabase, vehicle_id, "cancelled")
        return

    # ── P0-A: Evaluate price readiness + HITL trigger BEFORE DB save ──
    validation_info = card_summary.get("_validation", {})
    parsed_prices = validation_info.get("parsed_prices", {})
    price_is_present = parsed_prices.get("base") is not None

    hitl_needed, hitl_reasons = _needs_hitl_review(card_summary)

    if not price_is_present:
        initial_status = "needs_review"
        logger.warning(
            "[BG TASK] Readiness Check (Soft): Brak ceny bazowej "
            "(base_price) dla '%s %s' (vehicle_id=%s). "
            "Dane zostaną zapisane ze statusem 'needs_review'.",
            brand,
            model,
            vehicle_id,
        )
    elif hitl_needed:
        initial_status = "needs_review"
        logger.info(
            "[BG TASK] HITL trigger dla '%s %s' (vehicle_id=%s) — powody: %s",
            brand,
            model,
            vehicle_id,
            hitl_reasons[:8],  # cap to keep logs readable
        )
    else:
        initial_status = "enriching_features"

    # ── Normalize model/trim/body to SOT before persisting ──
    # The LLM sometimes leaks trim, brand prefix, engine specs, year codes, or
    # body type into the model field. We strip those out and reassign them to
    # the proper columns (trim_level / body_style in card_summary).
    cs = parsed_data.get("card_summary") or {}
    raw_trim_in_cs = cs.get("trim_level")
    raw_body_in_cs = cs.get("body_style")
    norm_model, norm_trim, norm_body = normalize_model_trim_body(
        raw_model=model,
        brand=brand,
        raw_trim=raw_trim_in_cs or trim,
        raw_body=raw_body_in_cs,
    )
    if norm_model and norm_model != model:
        logger.info(
            "[NORMALIZE] model %r -> %r (vehicle_id=%s)", model, norm_model, vehicle_id
        )
        model = norm_model
    if norm_trim != raw_trim_in_cs:
        logger.info(
            "[NORMALIZE] trim_level %r -> %r (vehicle_id=%s)",
            raw_trim_in_cs, norm_trim, vehicle_id,
        )
        cs["trim_level"] = norm_trim
        parsed_data["card_summary"] = cs
    if norm_body and norm_body != raw_body_in_cs:
        logger.info(
            "[NORMALIZE] body_style %r -> %r (vehicle_id=%s)",
            raw_body_in_cs, norm_body, vehicle_id,
        )
        cs["body_style"] = norm_body
        parsed_data["card_summary"] = cs

    # ── Composite body_style: join cabin + zabudowa signals ──
    # AI splits cabin info into card_summary.body_style and zabudowa info into
    # card_summary.service_equipment. SOT canon (Szablon_Wyceny_GCP) requires
    # the composite name (e.g. "Podwozie Brygadowe Skrzynia"), so we merge here.
    pre_compose_body = cs.get("body_style")
    # Production wywołanie: enable LLM fallback dla edge cases (nietypowe zabudowy,
    # sklejone PDF). Composer najpierw próbuje deterministycznej mapy (95% case),
    # potem Flash 2.5 dla pozostałych.
    composed_body = compose_body_style(
        pre_compose_body,
        cs.get("service_equipment"),
        enable_llm_fallback=True,
        card_summary=cs,
    )
    if composed_body and composed_body != pre_compose_body:
        logger.info(
            "[NORMALIZE] body_style composite %r -> %r (vehicle_id=%s)",
            pre_compose_body, composed_body, vehicle_id,
        )
        cs["body_style"] = composed_body
        parsed_data["card_summary"] = cs

    # ── P0-A: Partial save — always persist extracted data ──
    update_payload = {
        "brand": brand,
        "model": model,
        "offer_number": offer_number,
        "synthesis_data": parsed_data,
        "verification_status": initial_status,
        "raw_pdf_url": raw_pdf_url,
        "document_category": parsed_data.get("card_summary", {}).get("vehicle_class"),
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

    # ── P0-B: If price missing, flag for user fill-in but CONTINUE pipeline ──
    # Rationale: Audi configurator PDFs don't print a catalog base price (only
    # a final-after-options figure). Auto-promote from digital_twin.pricing
    # already happens in pipeline_price_validator; if even that yielded nothing,
    # we still want to enrich features, run samar mapping, generate embeddings,
    # etc., so the user can finish the record by entering the missing price.
    if not price_is_present:
        logger.warning(
            "[BG TASK] Brak ceny bazowej dla %s %s — kontynuuję enrichment, "
            "user musi ręcznie uzupełnić cenę. Vehicle: %s",
            brand,
            model,
            vehicle_id,
        )
        cs_inplace = parsed_data.setdefault("card_summary", {})
        requires = list(cs_inplace.get("_requires_user_input") or [])
        if "base_price" not in requires:
            requires.append("base_price")
        cs_inplace["_requires_user_input"] = requires
        # Persist flag immediately — downstream phases may crash on null price,
        # we want the FE to see the input field regardless.
        try:
            supabase.table("vehicle_synthesis").update(
                {"synthesis_data": parsed_data}
            ).eq("id", vehicle_id).execute()
        except Exception:
            logger.exception(
                "[BG TASK] Nie udało się zapisać flagi _requires_user_input dla %s",
                vehicle_id,
            )
        cache_invalidate_pattern("initial_data")
        cache_invalidate_pattern("filters:*")

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
    # Stays in "needs_review" if HITL trigger fires (low confidence per field,
    # hallucinated fields, validator with blocking severity, or legacy
    # _requires_user_input). Otherwise marked "completed".
    final_card_summary = parsed_data.get("card_summary", {})
    final_hitl_needed, _ = _needs_hitl_review(final_card_summary)
    final_status = "needs_review" if final_hitl_needed else "completed"
    logger.info(
        "[BG TASK] Oznaczam gotowość (stan: %s) dla %s", final_status, vehicle_id
    )
    supabase.table("vehicle_synthesis").update(
        {"verification_status": final_status}
    ).eq("id", vehicle_id).execute()

    # Trigger embedding generation. Strategia warstwowa, każda warstwa to
    # NIE-blokujące best-effort:
    #   1) primary: .delay() — async via Celery broker, włącza retry/backoff
    #      z dekoratora taska (5 retries z jitter, do 600s cap).
    #   2) secondary: .apply_async(countdown=30) — gdy broker chwilowo niedostępny
    #      ale za moment wstanie.
    #   3) fallback: zarejestruj vehicle_id w Redis SET kalk_v3:embedding:pending
    #      — `backfill_recent_vehicle_embeddings` (co 10 min) podniesie te ID
    #      jako fast lane. NIE odpalamy synchronicznie tutaj — blokowało to
    #      pipeline ekstrakcji i nie korzystało z retry/idempotency taska.
    try:
        logger.info(
            f"[BG TASK] Kolejkowanie generowania wektorów (Celery) dla {vehicle_id}"
        )
        generate_embedding_for_vehicle.delay(vehicle_id)
    except Exception as emb_e:
        logger.warning(
            f"[BG TASK] .delay() failed for {vehicle_id}: {emb_e!r} — próba apply_async(countdown=30)"
        )
        try:
            generate_embedding_for_vehicle.apply_async(
                args=[vehicle_id], countdown=30
            )
        except Exception as retry_e:
            # Ostatnia linia obrony: Redis SET → recent-backfill (10 min) złapie.
            logger.error(
                f"[BG TASK] apply_async też padło dla {vehicle_id}: {retry_e!r} — "
                "zarejestrowanie w embedding:pending dla recent-backfill"
            )
            try:
                from core.redis_cache import _get_client

                client = _get_client()
                if client is not None:
                    client.sadd("kalk_v3:embedding:pending", vehicle_id)
                    client.expire("kalk_v3:embedding:pending", 86400)  # 24h
            except Exception as redis_e:
                logger.error(
                    f"[BG TASK] Redis SADD też padł dla {vehicle_id}: {redis_e!r}"
                )

    cache_invalidate_pattern("initial_data")
    cache_invalidate_pattern("filters:*")

    logger.info(f"[BG TASK] Gotowe dla {vehicle_id}")
