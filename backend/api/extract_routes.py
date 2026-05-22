import json
import logging
import asyncio
import requests
from typing import Any, Dict
from pydantic import BaseModel
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import Response
from core.auth_middleware import require_role
from core.celery_tasks import process_document_task_from_storage
from services.ai_mapper_service import map_vehicle_data_flash
from core.database import supabase as supabase_client
from core.redis_cache import cache_invalidate_pattern
from core.settings import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from supabase import create_client

_supabase_admin = None


def _get_admin_client():
    """Lazy-init admin client — safe to call from inside endpoints."""
    global _supabase_admin
    if _supabase_admin is None and SUPABASE_SERVICE_ROLE_KEY:
        _supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_admin or supabase_client


logger = logging.getLogger(__name__)

router = APIRouter()


class ManualOverrideRequest(BaseModel):
    original_json: Dict[str, Any]
    user_prompt: str


@router.post("/extract/async")
async def extract_pdf_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    file_id: str = Form(...),
) -> Dict[str, Any]:
    # We allow pdf, excel, and image files to be sent to Gemini
    supported_extensions = (".pdf", ".xls", ".xlsx", ".png", ".jpg", ".jpeg")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    if not any(file.filename.lower().endswith(ext) for ext in supported_extensions):
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    try:
        file_bytes = await file.read()
        mime_type = file.content_type or "application/pdf"

        if not file.content_type:
            if file.filename.lower().endswith(".png"):
                mime_type = "image/png"
            elif file.filename.lower().endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"

        # Update status directly here:
        supabase_client.table("vehicle_synthesis").update(
            {"verification_status": "uploading"}
        ).eq("id", file_id).execute()

        from services.document_storage_service import (
            generate_safe_storage_path,
            upload_raw_vehicle_document,
        )

        storage_path = generate_safe_storage_path(file_id, file.filename)

        print(f"Uploading {file.filename} to Supabase Storage before queuing")

        # Upload using the admin client synchronous call inside to_thread to prevent blocking Event Loop
        await asyncio.to_thread(
            upload_raw_vehicle_document,
            file_bytes,
            storage_path,
            mime_type,
            _get_admin_client(),
        )

        print(
            f"Routing {file.filename} to universal extractor V2 from storage (Celery)"
        )
        await asyncio.to_thread(
            process_document_task_from_storage.delay,
            file_id=file_id,
            storage_path=storage_path,
            bucket_name="raw-vehicle-pdfs",
            file_name=file.filename,
            mime_type=mime_type,
            md5_hash="",
        )

        return {"status": "processing", "file_id": file_id}

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during extraction initialization: {str(e)}",
        )


class MapDataRequest(BaseModel):
    original_json: Dict[str, Any]


@router.post("/extract/map-vehicle-data")
def map_vehicle_data(request: MapDataRequest) -> Dict[str, Any]:
    try:
        print("Processing AI data mapping for vehicle JSON.")
        mapped_data = map_vehicle_data_flash(request.original_json)
        return mapped_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during AI data mapping: {str(e)}",
        )


class DiscountBackfillRequest(BaseModel):
    overwrite_existing: bool = False
    limit: int = 0  # 0 = bez limitu (tylko dla batch)


class DiscountOverrideRequest(BaseModel):
    explicit_rabat_pln: float | None = None
    discountable_base_net: float | None = None
    non_discountable_total_net: float | None = None
    audit_note: str | None = None


class FillBasePriceRequest(BaseModel):
    base_price: float
    domain: str = "brutto"  # "brutto" | "netto"
    options_price: float | None = None  # optional, same domain as base_price


class PriceDomainOverrideRequest(BaseModel):
    domain: str  # "netto" | "brutto"


class PriceDeduceRequest(BaseModel):
    """Częściowe kotwice cenowe od usera (wszystkie opcjonalne).

    Puste = dedukuj z obecnego card_summary. Read-only (preview) — nie zapisuje.
    """

    base_net: float | None = None
    base_gross: float | None = None
    options_net: float | None = None
    options_gross: float | None = None
    total_net: float | None = None
    total_gross: float | None = None
    service_net: float | None = None
    service_gross: float | None = None
    rabat_pln: float | None = None
    hint: str | None = None


class OptionDiscountFlag(BaseModel):
    field_id: str
    no_discount: bool


class ConfirmServiceComponent(BaseModel):
    """Składnik zabudowy/serwisu (np. Agregat, Kontener) — net+gross."""

    name: str
    net: float
    gross: float | None = None


class ConfirmFactoryOption(BaseModel):
    """Opcja fabryczna z poprawnym net/gross — aktualizuje pasującą paid_option."""

    field_id: str = ""
    name: str = ""
    net: float = 0.0
    gross: float | None = None
    no_discount: bool = False


class PriceConfirmRequest(BaseModel):
    """Finalne, zatwierdzone ceny — trwały zapis nadpisujący ekstrakcję."""

    domain: str = "netto"  # "netto" | "brutto"
    base_net: float
    base_gross: float | None = None
    discountable_options_net: float = 0.0
    non_discountable_options_net: float = 0.0
    service_net: float = 0.0
    service_gross: float | None = None
    total_net: float | None = None
    total_gross: float | None = None
    rabat_pln: float | None = None
    option_discount_flags: list[OptionDiscountFlag] = []
    # Optional: correct each factory paid_option's net/gross (matched by field_id
    # or exact name) so per-line prices agree with the totals.
    factory_options: list[ConfirmFactoryOption] = []
    # Optional: rewrite service_equipment (zabudowa) with its component split.
    service_name: str | None = None
    service_components: list[ConfirmServiceComponent] = []
    audit_note: str | None = None


# ── HITL Wizard payload models ──

class HITLPriceCorrection(BaseModel):
    """Pojedyncza korekta pozycji cenowej z wizarda HITL."""
    field_id: str
    bucket: str  # "base" | "factory" | "zabudowa" | "agregat" | "skip"
    price_value: float
    price_type: str  # "netto" | "brutto"
    vat_rate: float = 0.23


class HITLDiscountCorrection(BaseModel):
    """Korekta rabatu z wizarda HITL."""
    rabat_type: str  # "kwotowo" | "procentowo"
    rabat_basis: str  # "netto" | "brutto"
    rabat_value: float  # kwota (PLN) lub procent (0-100)
    discount_scope: list[str] = []  # ["base", "factory_options", ...]


class HITLApplyPayload(BaseModel):
    """Pełna paczka korekt z wizarda HITL — wysyłana z frontu na save."""
    price_corrections: list[HITLPriceCorrection] = []
    discount: HITLDiscountCorrection | None = None
    zabudowa_sot_key: str | None = None  # "KONTENER" | "CHLODNIA" | "IZOTERMA" | ...
    cabin_kind: str | None = None  # "podwozie" | "podwozie_brygadowe" | "furgon" | ...
    catalog_id_override: str | None = None
    trim_level_override: str | None = None
    engine_class_override: str | None = None
    duplicate_resolutions: Dict[str, str] = {}  # field_id → "keep" | "merge_into:<other_id>"
    currency: str = "PLN"
    user_notes: str = ""


class HITLPreviewPayload(BaseModel):
    """Dry-run preview — bez persist. Zwraca derived composite_body_style + WR%."""
    zabudowa_sot_key: str | None = None
    cabin_kind: str | None = None
    price_corrections: list[HITLPriceCorrection] = []
    discount: HITLDiscountCorrection | None = None


@router.post("/extract/backfill-discount/{vehicle_id}")
def backfill_discount_single(
    vehicle_id: str, request: DiscountBackfillRequest
) -> Dict[str, Any]:
    """Deterministyczny backfill `card_summary.discount` dla pojedynczego pojazdu.

    Idempotentny — domyślnie nie nadpisuje wpisów które już mają explicit_amount/percentage.
    Ustaw overwrite_existing=True by przeforsować rebuild (np. po zmianie reguł).
    """
    from core.discount_backfill import apply_backfill_to_card_summary

    # Use direct supabase client (admin _get_admin_client has stale schema state
    # that defaults to reverse_search for some reason).
    client = supabase_client
    resp = (
        client.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    synthesis = resp.data.get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary")
    if not isinstance(card_summary, dict):
        return {"status": "skipped", "reason": "no card_summary"}

    digital_twin = synthesis.get("digital_twin")
    changed = apply_backfill_to_card_summary(
        card_summary, digital_twin, overwrite_existing=request.overwrite_existing
    )

    if changed:
        synthesis["card_summary"] = card_summary
        # Direct httpx call — bypasses postgrest-py schema state issues.
        _direct_update_synthesis(vehicle_id, synthesis)
        cache_invalidate_pattern(f"vehicle:{vehicle_id}*")

    return {
        "status": "updated" if changed else "skipped",
        "vehicle_id": vehicle_id,
        "discount": card_summary.get("discount"),
    }


def _direct_update_synthesis(vehicle_id: str, synthesis: dict) -> None:
    """Direct UPDATE via psycopg2 — PostgREST in this Supabase instance has
    default schema set to `reverse_search` and ignores Content-Profile for
    vehicle_synthesis. We bypass it entirely with a direct DB connection.

    Falls back to `supabase_client.update()` when no DB password is configured
    (dev / test environments). The fallback writes through PostgREST and works
    as long as the local PostgREST default schema is `public`.
    """
    import psycopg2
    from psycopg2.extras import Json
    import os

    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        host = SUPABASE_URL.replace("https://", "").replace("http://", "").rstrip("/")
        ref = host.split(".")[0]
        password = os.getenv("SUPABASE_DB_PASSWORD")
        if not password:
            # Dev/test fallback: use PostgREST via supabase_client. Production
            # uses direct psycopg2 because PostgREST default schema isn't public.
            logger.info(
                "[UPDATE] SUPABASE_DB_PASSWORD not set — falling back to "
                "supabase_client.update() (dev mode)"
            )
            supabase_client.table("vehicle_synthesis").update(
                {"synthesis_data": synthesis}
            ).eq("id", vehicle_id).execute()
            return
        db_url = f"postgresql://postgres:{password}@db.{ref}.supabase.co:5432/postgres"

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.vehicle_synthesis SET synthesis_data = %s WHERE id = %s",
                (Json(synthesis), vehicle_id),
            )
        conn.commit()
    finally:
        conn.close()


@router.post("/extract/backfill-discount/all")
def backfill_discount_all(request: DiscountBackfillRequest) -> Dict[str, Any]:
    """Batch backfill — przelatuje wszystkie wpisy w `vehicle_synthesis`.

    Zwraca licznik (updated, skipped, errors). Bezpieczny do uruchomienia w produkcji
    bo każda iteracja jest idempotentna.
    """
    from core.discount_backfill import apply_backfill_to_card_summary

    # Use direct supabase client (admin _get_admin_client has stale schema state
    # that defaults to reverse_search for some reason).
    client = supabase_client
    query = client.table("vehicle_synthesis").select("id, synthesis_data")
    if request.limit and request.limit > 0:
        query = query.limit(request.limit)
    resp = query.execute()

    rows = resp.data or []
    updated = 0
    skipped = 0
    errors = 0

    for row in rows:
        try:
            synthesis = row.get("synthesis_data") or {}
            card_summary = synthesis.get("card_summary")
            if not isinstance(card_summary, dict):
                skipped += 1
                continue

            digital_twin = synthesis.get("digital_twin")
            changed = apply_backfill_to_card_summary(
                card_summary,
                digital_twin,
                overwrite_existing=request.overwrite_existing,
            )

            if changed:
                synthesis["card_summary"] = card_summary
                _direct_update_synthesis(row["id"], synthesis)
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            logger.exception("Backfill failed for vehicle %s: %s", row.get("id"), e)
            errors += 1

    cache_invalidate_pattern("initial_data")
    cache_invalidate_pattern("vehicle:*")

    return {
        "status": "ok",
        "total": len(rows),
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


@router.post("/extract/discount-override/{vehicle_id}")
def discount_override(
    vehicle_id: str, request: DiscountOverrideRequest
) -> Dict[str, Any]:
    """Manualne nadpisanie pól `discount` przez użytkownika z UI.

    Pozwala edytować `explicit_rabat_pln`, `discountable_base_net`,
    `non_discountable_total_net`. Przelicza `computed_pct` automatycznie.
    Confidence ustawiana na 1.0 i extraction_method na 'explicit_amount'.
    """
    client = supabase_client
    resp = (
        client.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    synthesis = resp.data.get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary")
    if not isinstance(card_summary, dict):
        raise HTTPException(status_code=400, detail="No card_summary to override")

    existing = card_summary.get("discount") or {}

    new_breakdown = {
        "explicit_rabat_pln": request.explicit_rabat_pln
        if request.explicit_rabat_pln is not None
        else existing.get("explicit_rabat_pln"),
        "explicit_rabat_pct": existing.get("explicit_rabat_pct"),
        "discountable_base_net": request.discountable_base_net
        if request.discountable_base_net is not None
        else existing.get("discountable_base_net"),
        "non_discountable_total_net": request.non_discountable_total_net
        if request.non_discountable_total_net is not None
        else existing.get("non_discountable_total_net"),
        "extraction_method": "explicit_amount",
        "confidence": 1.0,
        "audit_notes": list(existing.get("audit_notes") or []),
    }

    if request.audit_note:
        new_breakdown["audit_notes"].append(f"[OVERRIDE] {request.audit_note}")
    else:
        new_breakdown["audit_notes"].append("[OVERRIDE] Manualna korekta z UI")

    pln = new_breakdown.get("explicit_rabat_pln")
    base = new_breakdown.get("discountable_base_net")
    if pln and base:
        new_breakdown["computed_pct"] = round((float(pln) / float(base)) * 100, 2)
    else:
        new_breakdown["computed_pct"] = existing.get("computed_pct")

    card_summary["discount"] = new_breakdown
    if new_breakdown.get("computed_pct") is not None:
        card_summary["offer_discount_pct"] = str(new_breakdown["computed_pct"])
    if new_breakdown.get("explicit_rabat_pln") is not None:
        card_summary["offer_discount_pln"] = f"{int(new_breakdown['explicit_rabat_pln'])} PLN"

    synthesis["card_summary"] = card_summary
    _direct_update_synthesis(vehicle_id, synthesis)
    cache_invalidate_pattern(f"vehicle:{vehicle_id}*")

    return {"status": "ok", "vehicle_id": vehicle_id, "discount": new_breakdown}


@router.post("/extract/fill-base-price/{vehicle_id}")
def fill_base_price(
    vehicle_id: str, request: FillBasePriceRequest
) -> Dict[str, Any]:
    """User manually fills the base catalog price when AI couldn't extract it.

    Used for vehicles flagged with `card_summary._requires_user_input == ["base_price"]`
    (typically Audi configurator PDFs where the catalogue price isn't printed
    explicitly). Persists the price, re-runs the financial validator, and flips
    `verification_status` to "completed" when no inputs remain missing.
    """
    if request.base_price <= 0:
        raise HTTPException(
            status_code=400, detail="base_price must be > 0"
        )
    if request.domain not in ("brutto", "netto"):
        raise HTTPException(
            status_code=400, detail="domain must be 'brutto' or 'netto'"
        )

    client = supabase_client
    resp = (
        client.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    synthesis = resp.data.get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary")
    if not isinstance(card_summary, dict):
        card_summary = {}
        synthesis["card_summary"] = card_summary

    price_str = f"{int(round(request.base_price))} PLN {request.domain}"
    card_summary["base_price"] = price_str
    if request.options_price is not None and request.options_price >= 0:
        card_summary["options_price"] = (
            f"{int(round(request.options_price))} PLN {request.domain}"
        )

    # Keep price_domain in sync with the user-confirmed domain — without this
    # the UI's price-split widget (NETTO/BRUTTO columns) reads price_domain
    # rather than the suffix, and shows the entered brutto value in the netto
    # column (mismatched display, matrix calc misreads, etc.). The validator
    # rewrites _price_domain below, but the canonical price_domain stays.
    card_summary["price_domain"] = request.domain

    # Clear the user-input requirement for base_price
    requires = list(card_summary.get("_requires_user_input") or [])
    if "base_price" in requires:
        requires.remove("base_price")
    if requires:
        card_summary["_requires_user_input"] = requires
    else:
        card_summary.pop("_requires_user_input", None)

    # Re-run validator so _validation.parsed_prices and _price_domain refresh
    from core.pipeline_price_validator import validate_and_flag_prices

    synthesis = validate_and_flag_prices(synthesis)

    # Decide final verification_status
    remaining = synthesis.get("card_summary", {}).get("_requires_user_input")
    new_status = "needs_review" if remaining else "completed"

    _direct_update_synthesis(vehicle_id, synthesis)
    client.table("vehicle_synthesis").update(
        {"verification_status": new_status}
    ).eq("id", vehicle_id).execute()

    cache_invalidate_pattern(f"vehicle:{vehicle_id}*")
    cache_invalidate_pattern("initial_data")
    cache_invalidate_pattern("filters:*")

    return {
        "status": "ok",
        "vehicle_id": vehicle_id,
        "verification_status": new_status,
        "base_price": price_str,
        "remaining_user_inputs": remaining or [],
    }


@router.post("/extract/price-domain/{vehicle_id}")
def override_price_domain(
    vehicle_id: str, request: PriceDomainOverrideRequest
) -> Dict[str, Any]:
    """User flip-puje globalną interpretację cen między 'netto' a 'brutto'.

    Przypadek użycia: AI błędnie sklasyfikowało `price_domain` (np. 167 218.50
    z PDF oznaczone jako "Kwota brutto" potraktowane jako netto → cały UI ×1.23
    dwa razy). Jeden klik na badge "źródło: netto/brutto" odwraca interpretację
    bez zmiany wartości liczbowych — wszystkie kwoty z PDF są reinterpretowane.

    Aktualizuje `card_summary.price_domain` ORAZ `card_summary._price_domain`
    (drugi to override z walidatora). Zachowuje base_price/options_price/total_price
    jako stringi, ale uaktualnia sufiks "netto"/"brutto" w nich.
    """
    if request.domain not in ("netto", "brutto"):
        raise HTTPException(
            status_code=400, detail="domain must be 'netto' or 'brutto'"
        )

    client = supabase_client
    resp = (
        client.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    synthesis = resp.data.get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary")
    if not isinstance(card_summary, dict):
        raise HTTPException(status_code=400, detail="No card_summary to override")

    old_domain = card_summary.get("_price_domain") or card_summary.get("price_domain") or "unknown"
    card_summary["price_domain"] = request.domain
    card_summary["_price_domain"] = request.domain
    card_summary["_price_domain_overridden_by_user"] = True

    # Update sufiks netto/brutto w stringach base_price/options_price/total_price
    # bez zmiany wartości liczbowej (reinterpretacja, nie konwersja).
    import re

    def _swap_suffix(price_str: Any) -> Any:
        if not isinstance(price_str, str) or not price_str.strip():
            return price_str
        s = re.sub(r"\s*(netto|brutto)\s*$", "", price_str, flags=re.IGNORECASE).strip()
        return f"{s} {request.domain}"

    for k in ("base_price", "options_price", "total_price", "starting_price"):
        if k in card_summary:
            card_summary[k] = _swap_suffix(card_summary[k])

    # Audit trail
    audit = card_summary.setdefault("_audit_notes", [])
    if isinstance(audit, list):
        audit.append(
            f"[USER] price_domain flip: {old_domain} → {request.domain}"
        )

    # Re-run validator żeby _validation.parsed_prices się odświeżyło
    from core.pipeline_price_validator import validate_and_flag_prices

    synthesis["card_summary"] = card_summary
    synthesis = validate_and_flag_prices(synthesis)

    _direct_update_synthesis(vehicle_id, synthesis)
    cache_invalidate_pattern(f"vehicle:{vehicle_id}*")
    cache_invalidate_pattern("initial_data")
    cache_invalidate_pattern("filters:*")

    return {
        "status": "ok",
        "vehicle_id": vehicle_id,
        "old_domain": old_domain,
        "new_domain": request.domain,
        "base_price": synthesis["card_summary"].get("base_price"),
        "total_price": synthesis["card_summary"].get("total_price"),
    }


@router.post("/extract/price-deduce/{vehicle_id}")
def price_deduce(vehicle_id: str, request: PriceDeduceRequest) -> Dict[str, Any]:
    """LLM rekonstrukcja pełnego rozkładu ceny z częściowych danych (read-only preview).

    Uruchamiana na żądanie z panelu Audyt ceny dla luk, których deterministyczny
    walidator nie domyka (mieszane domeny netto/brutto, brakujące komponenty,
    brand-specyficzne nierabatowane opcje fabryczne). NIE zapisuje — zwraca
    sugestię; trwały zapis dopiero przez `/extract/price-confirm`.
    """
    from core.pipeline_price_deduction import deduce_prices

    client = supabase_client
    resp = (
        client.table("vehicle_synthesis")
        .select("id, synthesis_data, raw_pdf_url")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    card_summary = (resp.data.get("synthesis_data") or {}).get("card_summary")
    if not isinstance(card_summary, dict):
        raise HTTPException(status_code=400, detail="No card_summary to deduce from")

    # Fetch the source PDF so the LLM can read the netto/VAT/brutto summary and
    # determine the TRUE price domain (extraction frequently mislabels it). Best
    # effort — fall back to text-only deduction when the download fails.
    pdf_bytes: bytes | None = None
    raw_pdf_url = resp.data.get("raw_pdf_url")
    if raw_pdf_url:
        try:
            pdf_resp = requests.get(raw_pdf_url, timeout=30)
            if pdf_resp.ok and pdf_resp.content:
                pdf_bytes = pdf_resp.content
        except Exception as e:  # pragma: no cover — network best-effort
            logger.warning("[PRICE DEDUCE] PDF fetch failed (%s) — text-only", e)

    deduced = deduce_prices(
        card_summary, request.model_dump(exclude_none=True), pdf_bytes=pdf_bytes
    )
    if deduced is None:
        raise HTTPException(
            status_code=502,
            detail="Dedukcja LLM nieudana — spróbuj ponownie lub wpisz ceny ręcznie.",
        )

    return {"status": "ok", "vehicle_id": vehicle_id, "deduction": deduced}


@router.post("/extract/price-reconcile/{vehicle_id}")
def price_reconcile(vehicle_id: str, request: PriceDeduceRequest) -> Dict[str, Any]:
    """Multi-hypothesis price reconciliation (read-only preview).

    Re-runs the 4 net/brutto paths + LLM judge on demand from the Audyt-ceny panel
    and returns verdict + all paths + judge note. Does NOT persist — commit via
    `/extract/price-confirm`. The same engine runs automatically after every
    extraction (`extractor_v2`)."""
    from core.pipeline_price_reconciliation import reconcile_prices

    client = supabase_client
    resp = (
        client.table("vehicle_synthesis")
        .select("id, synthesis_data, raw_pdf_url")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    card_summary = (resp.data.get("synthesis_data") or {}).get("card_summary")
    if not isinstance(card_summary, dict):
        raise HTTPException(status_code=400, detail="No card_summary to reconcile")

    # Source PDF → the LLM judge reads the netto/VAT/brutto labels. Best effort.
    pdf_bytes: bytes | None = None
    raw_pdf_url = resp.data.get("raw_pdf_url")
    if raw_pdf_url:
        try:
            pdf_resp = requests.get(raw_pdf_url, timeout=30)
            if pdf_resp.ok and pdf_resp.content:
                pdf_bytes = pdf_resp.content
        except Exception as e:  # pragma: no cover — network best-effort
            logger.warning("[PRICE RECONCILE] PDF fetch failed (%s) — judge skipped", e)

    known = request.model_dump(exclude_none=True)
    result = reconcile_prices(
        card_summary, known=known or None, pdf_bytes=pdf_bytes, run_judge=True
    )
    return {"status": "ok", "vehicle_id": vehicle_id, "reconciliation": result.to_dict()}


@router.post("/extract/price-confirm/{vehicle_id}")
def price_confirm(vehicle_id: str, request: PriceConfirmRequest) -> Dict[str, Any]:
    """Trwały zapis zatwierdzonych cen — nadpisuje niepełną/wadliwą ekstrakcję + lock.

    Zapisuje finalne kwoty (stringi + pola V3 net/gross/vat), przelicza split rabatu
    (discountable vs non_discountable), oznacza opcje `no_discount` po field_id,
    ustawia lock `_price_confirmed`, re-uruchamia deterministyczny walidator
    (kontrola domknięcia — nie ufamy ślepo) i — gdy brak braków — flipuje status
    na 'completed' (wzór: fill_base_price).
    """
    if request.domain not in ("netto", "brutto"):
        raise HTTPException(status_code=400, detail="domain must be 'netto' or 'brutto'")
    if request.base_net <= 0:
        raise HTTPException(status_code=400, detail="base_net must be > 0")

    _VAT = 1.23

    client = supabase_client
    resp = (
        client.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    synthesis = resp.data.get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary")
    if not isinstance(card_summary, dict):
        card_summary = {}
        synthesis["card_summary"] = card_summary

    base_net = float(request.base_net)
    base_gross = float(request.base_gross) if request.base_gross else round(base_net * _VAT, 2)
    disc_opt_net = float(request.discountable_options_net or 0.0)
    nondisc_opt_net = float(request.non_discountable_options_net or 0.0)
    service_net = float(request.service_net or 0.0)
    rabat = float(request.rabat_pln or 0.0)

    options_net = disc_opt_net + nondisc_opt_net
    options_gross = round(options_net * _VAT, 2)

    total_net = (
        float(request.total_net)
        if request.total_net is not None
        else base_net + options_net + service_net - rabat
    )
    total_gross = (
        float(request.total_gross) if request.total_gross else round(total_net * _VAT, 2)
    )

    def _vat_of(net: float, gross: float) -> float:
        return round(gross / net - 1.0, 4) if net > 0 else 0.23

    def _fmt(net: float, gross: float) -> str:
        val = net if request.domain == "netto" else gross
        return f"{int(round(val))} PLN {request.domain}"

    card_summary["base_price"] = _fmt(base_net, base_gross)
    card_summary["options_price"] = _fmt(options_net, options_gross)
    card_summary["total_price"] = _fmt(total_net, total_gross)
    card_summary["price_domain"] = request.domain

    card_summary["base_price_net"] = base_net
    card_summary["base_price_gross"] = base_gross
    card_summary["base_price_vat"] = _vat_of(base_net, base_gross)
    card_summary["options_price_net"] = options_net
    card_summary["options_price_gross"] = options_gross
    card_summary["options_price_vat"] = 0.23
    card_summary["total_price_net"] = total_net
    card_summary["total_price_gross"] = total_gross
    card_summary["total_price_vat"] = _vat_of(total_net, total_gross)

    # ── Discount split (discountable = base + opcje rabatowane) ──
    existing_discount = card_summary.get("discount") or {}
    discountable_base = base_net + disc_opt_net
    non_discountable_total = nondisc_opt_net + service_net
    computed_pct = (
        round((rabat / discountable_base) * 100, 2)
        if (rabat and discountable_base)
        else existing_discount.get("computed_pct")
    )
    notes = list(existing_discount.get("audit_notes") or [])
    notes.append(
        f"[ZATWIERDZONE] {request.audit_note}"
        if request.audit_note
        else "[ZATWIERDZONE] Cena zatwierdzona ręcznie z panelu Audyt ceny"
    )
    card_summary["discount"] = {
        "explicit_rabat_pln": rabat if rabat else existing_discount.get("explicit_rabat_pln"),
        "explicit_rabat_pct": existing_discount.get("explicit_rabat_pct"),
        "discountable_base_net": discountable_base,
        "non_discountable_total_net": non_discountable_total,
        "computed_pct": computed_pct,
        "extraction_method": "explicit_amount",
        "confidence": 1.0,
        "audit_notes": notes,
    }
    if computed_pct is not None:
        card_summary["offer_discount_pct"] = str(computed_pct)
    if rabat:
        card_summary["offer_discount_pln"] = f"{int(rabat)} PLN"

    # ── Write service_equipment (zabudowa) with component split + net/gross ──
    # Only when there is service data; otherwise the existing block is left
    # untouched (additive — never blanks an existing zabudowa).
    if request.service_components or service_net > 0:
        service_gross = (
            float(request.service_gross)
            if request.service_gross
            else round(service_net * _VAT, 2)
        )
        se = card_summary.get("service_equipment")
        if not isinstance(se, dict):
            se = {}
        if request.service_name:
            se["name"] = request.service_name
        elif not se.get("name"):
            se["name"] = "Zabudowa / wyposażenie serwisowe"
        se["total_price_net"] = f"{service_net:.2f} PLN netto"
        se["total_price_gross"] = f"{service_gross:.2f} PLN brutto"
        se["net_amount"] = round(service_net, 2)
        se["gross_amount"] = service_gross
        if request.service_components:
            se["components"] = [
                {
                    "name": c.name,
                    "price_net": f"{float(c.net):.2f} PLN netto",
                    "price_gross": (
                        f"{float(c.gross):.2f} PLN brutto"
                        if c.gross
                        else f"{round(float(c.net) * _VAT, 2):.2f} PLN brutto"
                    ),
                    "net_amount": round(float(c.net), 2),
                    "gross_amount": (
                        round(float(c.gross), 2)
                        if c.gross
                        else round(float(c.net) * _VAT, 2)
                    ),
                }
                for c in request.service_components
            ]
        card_summary["service_equipment"] = se

    # ── Apply per-option no_discount flags (reuse existing mechanism) ──
    if request.option_discount_flags:
        flag_map = {f.field_id: f.no_discount for f in request.option_discount_flags if f.field_id}
        for opt in card_summary.get("paid_options") or []:
            if isinstance(opt, dict) and opt.get("field_id") in flag_map:
                opt["no_discount"] = flag_map[opt["field_id"]]

    # ── Correct each factory paid_option's net/gross (match by field_id or name) ──
    # Keeps per-line prices consistent with the confirmed totals so the live
    # calculator and OPTIONS_SUM_MISMATCH agree. Only updates matching entries —
    # never adds or removes options.
    if request.factory_options:
        by_id = {f.field_id: f for f in request.factory_options if f.field_id}
        by_name = {f.name.strip().lower(): f for f in request.factory_options if f.name}
        for opt in card_summary.get("paid_options") or []:
            if not isinstance(opt, dict):
                continue
            fo = by_id.get(opt.get("field_id") or "") or by_name.get(
                str(opt.get("name", "")).strip().lower()
            )
            if fo is None:
                continue
            fo_net = float(fo.net)
            fo_gross = float(fo.gross) if fo.gross else round(fo_net * _VAT, 2)
            opt["price"] = f"{fo_net:.2f} PLN netto"
            opt["price_type"] = "netto"
            opt["price_net"] = fo_net
            opt["net_amount"] = fo_net
            opt["gross_amount"] = fo_gross
            opt["no_discount"] = fo.no_discount

    # ── Lock markers ──
    card_summary["_price_confirmed"] = True
    breakdown = card_summary.setdefault("confidence_breakdown", {})
    for key in ("base_price", "options_price", "total_price"):
        breakdown[key] = 1.0
    requires = list(card_summary.get("_requires_user_input") or [])
    if "base_price" in requires:
        requires.remove("base_price")
    if requires:
        card_summary["_requires_user_input"] = requires
    else:
        card_summary.pop("_requires_user_input", None)

    # ── Re-run deterministic validator (closure check — don't trust blindly) ──
    from core.pipeline_price_validator import (
        soften_discount_blind_warnings,
        validate_and_flag_prices,
    )

    synthesis["card_summary"] = card_summary
    synthesis = validate_and_flag_prices(synthesis)
    # Confirmed + discount triangulation closes → the base+options-vs-total gap
    # equals the rabat (expected), so downgrade those discount-blind ERRORs.
    soften_discount_blind_warnings(synthesis.get("card_summary", {}))

    remaining = synthesis.get("card_summary", {}).get("_requires_user_input")
    new_status = "needs_review" if remaining else "completed"

    _direct_update_synthesis(vehicle_id, synthesis)
    client.table("vehicle_synthesis").update(
        {"verification_status": new_status}
    ).eq("id", vehicle_id).execute()
    cache_invalidate_pattern(f"vehicle:{vehicle_id}*")
    cache_invalidate_pattern("initial_data")
    cache_invalidate_pattern("filters:*")

    return {
        "status": "ok",
        "vehicle_id": vehicle_id,
        "verification_status": new_status,
        "validation": synthesis.get("card_summary", {}).get("_validation"),
    }


# ── HITL Wizard endpoints ──

def _compute_capex_from_corrections(
    price_corrections: list[HITLPriceCorrection],
) -> Dict[str, float]:
    """Suma per bucket, znormalizowana do brutto (VAT-inclusive)."""
    sums = {"base": 0.0, "factory": 0.0, "zabudowa": 0.0, "agregat": 0.0}
    for pc in price_corrections:
        if pc.bucket == "skip" or pc.bucket not in sums:
            continue
        gross = pc.price_value if pc.price_type == "brutto" else pc.price_value * (1 + pc.vat_rate)
        sums[pc.bucket] += gross
    sums["total_capex"] = sum(sums.values())
    return sums


def _resolve_body_type_for_composite(composite_name: str | None) -> Dict[str, Any] | None:
    """Lookup body_types row dla composite SOT name (SOT-backed).

    Używa `body_type_matcher.match_body_type` (fuzzy match → body_types.id) +
    `samar_rv_fetchers.fetch_body_correction_cached` (utrata_wartosci per id).
    Zwraca dict z body_type_id, matched_name, utrata_wartosci. None gdy brak match.
    """
    if not composite_name:
        return None
    try:
        from core.body_type_matcher import match_body_type
        from core.samar_rv_fetchers import fetch_body_correction_cached

        match = match_body_type(composite_name)
        if not match or not match.matched_body_type_id:
            return None
        utrata = fetch_body_correction_cached(match.matched_body_type_id)
        return {
            "body_type_id": match.matched_body_type_id,
            "matched_name": match.matched_name,
            "vehicle_class": match.vehicle_class,
            "match_method": match.match_method,
            "score": match.score,
            "utrata_wartosci": utrata,
        }
    except Exception as e:
        logger.warning("[HITL] body_type lookup failed for %r: %s", composite_name, e)
        return None


@router.post("/extract/hitl/preview/{vehicle_id}")
def hitl_preview(vehicle_id: str, payload: HITLPreviewPayload) -> Dict[str, Any]:
    """Dry-run preview wizarda HITL — zwraca derived composite_body_style, SAMAR-relevant
    body_type lookup i CAPEX summary z user korekt, BEZ persist.

    Wywoływany on-the-fly z UI po każdej zmianie drag-drop / wyboru zabudowy.
    """
    from core.composite_body_style import recompose_with_override

    # Pull synthesis for context (KONTENER promotion uses body_style/service_equipment text)
    resp = (
        supabase_client.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    synthesis = resp.data.get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary") or {}

    composite = recompose_with_override(
        cabin_kind=payload.cabin_kind,
        zabudowa_sot_key=payload.zabudowa_sot_key,
        enable_llm_fallback=False,  # preview ma być szybki, bez LLM
        card_summary=card_summary,
    )

    body_type_info = _resolve_body_type_for_composite(composite)
    capex = _compute_capex_from_corrections(payload.price_corrections)

    return {
        "vehicle_id": vehicle_id,
        "composite_body_style": composite,
        "body_type": body_type_info,
        "capex": capex,
        "discount_preview": payload.discount.model_dump() if payload.discount else None,
    }


@router.post("/extract/hitl/apply/{vehicle_id}")
def hitl_apply(vehicle_id: str, payload: HITLApplyPayload) -> Dict[str, Any]:
    """Finalna aplikacja korekt z wizarda HITL.

    Workflow:
    1. Pobierz vehicle_synthesis.synthesis_data
    2. Re-klasyfikuj paid_options per bucket assignment z payload
    3. Re-run composite_body_style z override
    4. Update card_summary.discount (rabat_type/basis/scope + computed_pct)
    5. Update vehicle_synthesis, set verification_status='completed'
    6. Log do extraction_corrections (training signal dla few-shot)
    """
    from core.composite_body_style import recompose_with_override
    from core.pipeline_price_validator import validate_and_flag_prices

    client = supabase_client
    resp = (
        client.table("vehicle_synthesis")
        .select("id, synthesis_data, brand, model")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    synthesis = resp.data.get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary")
    if not isinstance(card_summary, dict):
        raise HTTPException(
            status_code=400, detail="No card_summary to apply HITL corrections to"
        )
    brand = resp.data.get("brand")
    model = resp.data.get("model")

    # ── 1. Re-classify paid_options per bucket ──
    # field_id → bucket lookup
    bucket_by_field: Dict[str, str] = {pc.field_id: pc.bucket for pc in payload.price_corrections}
    price_by_field: Dict[str, tuple[float, str, float]] = {
        pc.field_id: (pc.price_value, pc.price_type, pc.vat_rate)
        for pc in payload.price_corrections
    }

    paid_options = card_summary.get("paid_options") or []
    new_paid: list[dict[str, Any]] = []
    new_service_components: list[dict[str, Any]] = []

    for opt in paid_options:
        if not isinstance(opt, dict):
            continue
        fid = opt.get("field_id", "")
        bucket = bucket_by_field.get(fid)
        if bucket == "skip":
            continue  # drop
        # Update price/type from user correction
        if fid in price_by_field:
            val, ptype, vat = price_by_field[fid]
            opt["price"] = f"{val} PLN {ptype}"
            opt["price_type"] = ptype
            # Preserve original extraction confidence in audit metadata so we
            # can tell later what the model thought before the user override.
            # Apply confidence=1.0 only for the user-confirmed correction.
            prev_conf = opt.get("confidence")
            if prev_conf is not None and prev_conf != 1.0:
                opt.setdefault("confidence_before_hitl", prev_conf)
            opt["confidence"] = 1.0  # user-confirmed
        if bucket in ("zabudowa", "agregat"):
            # Move to service_equipment.components
            gross = (
                opt_price_value(opt)
                if opt.get("price_type") == "brutto"
                else opt_price_value(opt) * (1 + 0.23)
            )
            new_service_components.append(
                {
                    "name": opt.get("name", ""),
                    "price_net": str(opt_price_value(opt) / (1 + 0.23) if opt.get("price_type") == "brutto" else opt_price_value(opt)),
                    "price_gross": str(gross),
                    "confidence": 1.0,
                    "field_id": fid,
                }
            )
        else:
            # bucket "base" / "factory" / None → stay in paid_options
            if bucket == "base":
                opt["category"] = "Bazowa"
            elif bucket == "factory":
                opt["category"] = "Fabryczna"
            new_paid.append(opt)

    card_summary["paid_options"] = new_paid

    if new_service_components:
        se = card_summary.get("service_equipment") or {}
        if not isinstance(se, dict):
            se = {}
        # Replace: HITL is authoritative
        se["components"] = new_service_components
        if not se.get("name"):
            se["name"] = "Zabudowa specjalistyczna"
        card_summary["service_equipment"] = se

    # ── 2. Re-run composite_body_style ──
    composite = recompose_with_override(
        cabin_kind=payload.cabin_kind,
        zabudowa_sot_key=payload.zabudowa_sot_key,
        enable_llm_fallback=True,
        card_summary=card_summary,
    )
    if composite:
        card_summary["body_style"] = composite

    # ── 3. Update discount ──
    if payload.discount is not None:
        existing = card_summary.get("discount") or {}
        d = payload.discount
        new_discount = dict(existing)
        new_discount["rabat_type"] = d.rabat_type
        new_discount["rabat_basis"] = d.rabat_basis
        new_discount["discount_scope"] = d.discount_scope
        prev_disc_conf = existing.get("confidence")
        if prev_disc_conf is not None and prev_disc_conf != 1.0:
            new_discount.setdefault("confidence_before_hitl", prev_disc_conf)
        new_discount["confidence"] = 1.0
        new_discount["extraction_method"] = "explicit_amount" if d.rabat_type == "kwotowo" else "explicit_percentage"
        if d.rabat_type == "kwotowo":
            new_discount["explicit_rabat_pln"] = d.rabat_value
        else:
            new_discount["explicit_rabat_pct"] = d.rabat_value
        audit = list(new_discount.get("audit_notes") or [])
        audit.append(f"[HITL] rabat={d.rabat_type}:{d.rabat_value} basis={d.rabat_basis} scope={d.discount_scope}")
        new_discount["audit_notes"] = audit
        card_summary["discount"] = new_discount

    # ── 4. Optional trim/engine/catalog override ──
    if payload.trim_level_override:
        card_summary["trim_level"] = payload.trim_level_override
    if payload.engine_class_override:
        mapped = synthesis.get("mapped_ai_data") or {}
        mapped["engine_class"] = payload.engine_class_override
        synthesis["mapped_ai_data"] = mapped
    if payload.catalog_id_override:
        synthesis["suggested_catalog"] = {"catalog_id": payload.catalog_id_override, "manual_override": True}

    # ── 5. Re-validate after corrections ──
    synthesis["card_summary"] = card_summary
    synthesis = validate_and_flag_prices(synthesis)

    # ── 5b. One-shot SOT mapping for manual-blank flow ──
    # When a vehicle was created via POST /extract/blank (no PDF extraction
    # ran), the engines / samar_classes / mapped_ai_data fields are empty.
    # First successful HITL apply triggers finalize_vehicle_pipeline to fill
    # them, then pops the _origin marker so subsequent edits stay HITL-only.
    was_manual_blank = synthesis.get("_origin") == "manual_blank"
    if was_manual_blank:
        fuel_val = card_summary.get("fuel")
        if not fuel_val or fuel_val == "Brak":
            # map_to_engine_class requires a non-empty fuel — fail fast with
            # a structured error so the UI can highlight the missing field.
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "missing_required_for_sot_mapping",
                    "message": (
                        "Pole 'fuel' jest wymagane przed pierwszym Apply "
                        "(mapper silnika SOT nie zadziała bez niego)."
                    ),
                    "requires_user_input": ["fuel"],
                },
            )
        try:
            from core.extraction_pipeline.phase_2_mapping import (
                finalize_vehicle_pipeline,
            )

            finalize_vehicle_pipeline(
                supabase_client,
                vehicle_id,
                synthesis,
                raw_pdf_url=None,
                parent_file_id=vehicle_id,
                document_markdown=None,
            )
            synthesis.pop("_origin", None)
            logger.info(
                "[HITL] manual_blank one-shot SOT mapping completed for %s",
                vehicle_id,
            )
        except HTTPException:
            raise
        except Exception as sot_err:
            logger.exception(
                "[HITL] manual_blank SOT mapping failed for %s: %s",
                vehicle_id,
                sot_err,
            )
            # Don't block the apply — leave _origin in place so user can
            # retry after fixing whatever input was wrong.
            pass

    # ── 6. Persist + flip status ──
    _direct_update_synthesis(vehicle_id, synthesis)
    client.table("vehicle_synthesis").update(
        {"verification_status": "completed"}
    ).eq("id", vehicle_id).execute()

    # ── 7. Log do extraction_corrections (best-effort, admin client by-passuje RLS) ──
    try:
        _get_admin_client().table("extraction_corrections").insert(
            {
                "vehicle_id": vehicle_id,
                "brand": brand,
                "model": model,
                "field_name": "hitl_bucket",
                "old_value": "(see synthesis_data prior version)",
                "new_value": payload.model_dump_json(),
                "context_notes": payload.user_notes or None,
            }
        ).execute()
    except Exception as log_err:
        logger.warning("[HITL] extraction_corrections insert failed: %s", log_err)

    cache_invalidate_pattern(f"vehicle:{vehicle_id}*")
    cache_invalidate_pattern("initial_data")
    cache_invalidate_pattern("filters:*")

    # ── 8. For manual-blank: rebuild auto-kalkulacja with fresh mapped_ai_data ──
    # The auto matrix cache was created at /extract/blank time with empty
    # brand/model/fuel/samar (SOT hadn't run yet). Now that SOT mapping
    # populated mapped_ai_data, re-dispatch the refresh so the existing
    # AUTO ltr_kalkulacje row gets updated with engine_name + samar_category
    # (refresh_matrix_cache_for_vehicles uses upsert-by-vehicle_id, so we
    # update rather than duplicate).
    if was_manual_blank:
        try:
            from tasks.matrix_tasks import (  # noqa: PLC0415
                refresh_matrix_cache_for_vehicles_task,
            )

            refresh_matrix_cache_for_vehicles_task.apply_async(args=[[vehicle_id]])
            logger.info(
                "[HITL] manual_blank %s — dispatched matrix refresh task", vehicle_id
            )
        except Exception as refresh_err:
            # Non-fatal: user can still click "Przelicz" in UI to force-create
            # a fresh kalkulacja. Just log and continue.
            logger.warning(
                "[HITL] manual_blank %s — matrix refresh dispatch failed: %s",
                vehicle_id,
                refresh_err,
            )

    body_type_info = _resolve_body_type_for_composite(composite)
    capex = _compute_capex_from_corrections(payload.price_corrections)

    return {
        "status": "ok",
        "vehicle_id": vehicle_id,
        "verification_status": "completed",
        "composite_body_style": composite,
        "body_type": body_type_info,
        "capex": capex,
    }


def opt_price_value(opt: Dict[str, Any]) -> float:
    """Pomocniczy parse float z pola price (z fallbackiem 0.0)."""
    from core.price_parser import parse_price_string

    parsed = parse_price_string(opt.get("price", ""))
    return float(parsed.value) if parsed else 0.0


@router.post("/extract/remap-classification")
def remap_classification(request: MapDataRequest) -> Dict[str, Any]:
    """
    Full classification pipeline: Flash mapper → Engine → SAMAR.
    Returns mapped_ai_data with samar_category, engine_class, candidates.
    """
    from services.classification_service import run_full_classification_pipeline

    try:
        return run_full_classification_pipeline(request.original_json)
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Classification pipeline error: {str(e)}",
        )


_PDF_PROXY_ALLOWED_HOSTS = frozenset(
    {
        # Supabase Storage — the only place we host raw PDFs we proxy.
        "gnpsdiarmwvqhqbyetce.supabase.co",
        "supabase.co",
    }
)
_PDF_PROXY_MAX_BYTES = 50 * 1024 * 1024  # 50 MB hard cap


@router.get("/pdf-proxy")
def proxy_pdf(url: str):
    """Proxy a PDF from an allow-listed host.

    Protections against SSRF / DoS:
    - HTTPS only.
    - Host must end in one of `_PDF_PROXY_ALLOWED_HOSTS` (no LAN/cloud-metadata).
    - Body capped at `_PDF_PROXY_MAX_BYTES` (50 MB) via stream + early abort.
    - Network timeout (10s connect, 30s read).
    """
    from urllib.parse import urlparse

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Only https:// URLs allowed")
    host = (parsed.hostname or "").lower()
    if not host or not any(
        host == allowed or host.endswith("." + allowed)
        for allowed in _PDF_PROXY_ALLOWED_HOSTS
    ):
        raise HTTPException(
            status_code=400, detail="Host not in PDF proxy allow-list"
        )

    try:
        with requests.get(url, stream=True, timeout=(10, 30)) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
                raise HTTPException(
                    status_code=415, detail=f"Upstream returned non-PDF: {content_type}"
                )
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > _PDF_PROXY_MAX_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"PDF exceeds {_PDF_PROXY_MAX_BYTES // (1024 * 1024)} MB limit",
                    )
                chunks.append(chunk)
        return Response(
            content=b"".join(chunks),
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="document.pdf"',
                "Accept-Ranges": "bytes",
                "Cross-Origin-Resource-Policy": "cross-origin",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error proxying PDF from %s: %s", host, e)
        raise HTTPException(status_code=502, detail="Failed to fetch upstream PDF")


_MIME_MAP: dict[str, str] = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class DeleteVehicleRequest(BaseModel):
    vehicle_id: str


@router.post("/delete-vehicle")
def delete_vehicle(request: DeleteVehicleRequest) -> Dict[str, Any]:
    try:
        client = _get_admin_client()
        print(f"Deleting vehicle strictly from synthesis with ID: {request.vehicle_id}")

        resp = (
            client.table("vehicle_synthesis")
            .delete()
            .eq("id", request.vehicle_id)
            .execute()
        )

        if not resp.data:
            raise HTTPException(
                status_code=404, detail="Vehicle not found or already deleted"
            )

        # Invalidate cache for frontend filters
        cache_invalidate_pattern("initial_data")
        cache_invalidate_pattern("filters:*")

        return {"status": "success", "message": "Vehicle deleted successfully"}
    except Exception as e:
        print(f"Error deleting vehicle: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete vehicle")


class CancelProcessingRequest(BaseModel):
    vehicle_id: str


@router.post("/cancel-processing")
def cancel_processing(request: CancelProcessingRequest) -> Dict[str, Any]:
    """
    Immediately cancels document processing:
    1. Sets DB status to 'cancelled' → triggers Supabase Realtime → instant UI update
    2. Celery task polls DB status and stops gracefully
    """
    try:
        # 1. Immediately update DB — frontend sees this via Realtime
        supabase_client.table("vehicle_synthesis").update(
            {"verification_status": "cancelled"}
        ).eq("id", request.vehicle_id).execute()

        print(f"[CANCEL] Vehicle {request.vehicle_id} DB status updated to cancelled.")

        return {
            "status": "cancelled",
            "message": "Przetwarzanie zostało anulowane.",
        }
    except Exception as e:
        print(f"Error cancelling processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel processing")


# --- Batch Delete ---


class BatchDeleteRequest(BaseModel):
    vehicle_ids: list[str]


@router.post(
    "/delete-vehicles-batch",
    dependencies=[Depends(require_role("admin"))],
)
def delete_vehicles_batch(request: BatchDeleteRequest) -> Dict[str, Any]:
    """Delete multiple vehicles in a single transaction."""
    if not request.vehicle_ids:
        raise HTTPException(status_code=400, detail="No vehicle IDs provided.")

    try:
        client = _get_admin_client()
        print(f"Batch deleting {len(request.vehicle_ids)} vehicles")
        resp = (
            client.table("vehicle_synthesis")
            .delete()
            .in_("id", request.vehicle_ids)
            .execute()
        )

        if not resp.data:
            print("No vehicles were found to delete in batch.")

        # Invalidate cache for frontend filters
        cache_invalidate_pattern("initial_data")
        cache_invalidate_pattern("filters:*")

        return {
            "status": "success",
            "deleted_count": len(request.vehicle_ids),
        }
    except Exception as e:
        print(f"Error batch deleting vehicles: {e}")
        raise HTTPException(status_code=500, detail="Failed to batch delete")


# --- AI Vehicle Comparison ---


class CompareVehiclesRequest(BaseModel):
    vehicle_ids: list[str]


def _extract_comparison_payload(
    synthesis_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Extract key fields for comparison prompt.
    Includes: card_summary, technical_data, mapped_ai_data,
    paid_options, standard_equipment, visual_identity.
    """
    if not synthesis_data:
        return {}

    payload: dict[str, Any] = {}

    # Card summary (prices, powertrain, emissions, fuel, body)
    card = synthesis_data.get("card_summary")
    if card:
        payload["card_summary"] = card

    # Technical data (dimensions, weights, engine, EV range)
    tech = synthesis_data.get("technical_data")
    if tech:
        payload["technical_data"] = tech

    # Mapped AI classification (SAMAR, engine class)
    mapped = synthesis_data.get("mapped_ai_data")
    if mapped:
        payload["mapped_ai_data"] = mapped

    # Equipment
    std_equip = synthesis_data.get("standard_equipment")
    if std_equip:
        payload["standard_equipment"] = std_equip

    opt_equip = synthesis_data.get("optional_equipment")
    if opt_equip:
        payload["optional_equipment"] = opt_equip

    # Visual identity
    visual = synthesis_data.get("visual_identity")
    if visual:
        payload["visual_identity"] = visual

    # Financing options
    financing = synthesis_data.get("financing")
    if financing:
        payload["financing"] = financing

    # Service equipment
    svc = synthesis_data.get("service_equipment")
    if svc:
        payload["service_equipment"] = svc

    return payload


@router.post("/compare-vehicles")
def compare_vehicles(request: CompareVehiclesRequest) -> Dict[str, Any]:
    """
    Compare 2-5 vehicles using Gemini Flash.
    Extracts key data from synthesis_data and produces a markdown comparison.
    """
    from core.gemini_client import get_gemini_client
    from google.genai import types as genai_types

    if len(request.vehicle_ids) < 2:
        raise HTTPException(status_code=400, detail="Minimum 2 vehicles required.")
    if len(request.vehicle_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 vehicles.")

    try:
        # Fetch vehicles
        result = (
            supabase_client.table("vehicle_synthesis")
            .select("id, brand, model, synthesis_data")
            .in_("id", request.vehicle_ids)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Vehicles not found.")

        # Build comparison payloads
        vehicle_payloads = []
        for row in result.data:
            synthesis = row.get("synthesis_data") or {}
            mapped = synthesis.get("mapped_ai_data") or {}
            trim = mapped.get("trim_level", "")
            name = f"{row.get('brand', '?')} {row.get('model', '')} {trim}".strip()
            payload = _extract_comparison_payload(row.get("synthesis_data"))
            vehicle_payloads.append({"name": name, "data": payload})

        # Build prompt
        vehicles_json = json.dumps(vehicle_payloads, ensure_ascii=False, indent=2)

        prompt = f"""Jesteś ekspertem ds. floty samochodowej. Porównaj poniższe pojazdy w zwięzłej, profesjonalnej tabeli markdown.

WYMAGANIA:
1. Tabela z kolumnami: Cecha | {" | ".join(v["name"] for v in vehicle_payloads)}
2. Uwzględnij: cena katalogowa, rabat, cena po rabacie, moc, silnik, napęd, skrzynia, emisje WLTP, spalanie, masa własna/DMC, wymiary, koła, typ nadwozia
3. Dodaj sekcję "Wyposażenie standardowe" — pokaż kluczowe różnice (co jeden ma, a drugi nie)
4. Dodaj sekcję "Opcje płatne" — pokaż łączną wartość opcji i najważniejsze pozycje
5. Na końcu dodaj krótkie **Podsumowanie** (2-3 zdania) — value for money, TCO, rekomendacja
6. Bądź MAKSYMALNIE ZWIĘZŁY. Nie powtarzaj danych z tabeli w podsumowaniu.
7. Wszystkie ceny w PLN, masy w kg, wymiary w mm.

DANE POJAZDÓW:
{vehicles_json}"""

        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.0,
            ),
        )

        markdown_result = response.text if response.text else "Brak wyniku."

        return {"markdown": markdown_result}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error comparing vehicles: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Vehicle comparison failed: {str(e)}",
        )


@router.get("/kalkulator/pojazd/{vehicle_id}")
def get_vehicle_synthesis(vehicle_id: str, lite: bool = False) -> Dict[str, Any]:
    """Zwraca synthesis_data pojazdu po ID — używane przez VehicleFeaturesCard.
    lite=True zwraca tylko niezbędne pola dla cache cech (standard_equipment, paid_options, suggested_catalog).
    """
    from core.database import get_fresh_client
    from httpcore import RemoteProtocolError as HttpcoreRemoteProtocolError
    from httpx import RemoteProtocolError as HttpxRemoteProtocolError

    def _fetch(client) -> Dict[str, Any]:
        response = (
            client.table("vehicle_synthesis")
            .select("id, brand, model, synthesis_data, verification_status")
            .eq("id", vehicle_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Pojazd nie znaleziony")
        row = response.data[0]
        synthesis = row.get("synthesis_data") or {}
        mapped = synthesis.get("mapped_ai_data") or {}
        trim = mapped.get("trim_level", "")

        # Optional Lite mode: Filter payload to minimize size for preloading
        if lite:
            card_summary = synthesis.get("card_summary") or {}
            synthesis = {
                "card_summary": {
                    "standard_equipment": card_summary.get("standard_equipment", []),
                    "paid_options": card_summary.get("paid_options", []),
                },
                "suggested_catalog": synthesis.get("suggested_catalog"),
            }

        # Log payload size for diagnosis
        payload_size = len(str(synthesis))
        logger.info(
            "Fetch synthesis successful: id=%s size=%d chars", vehicle_id, payload_size
        )

        return {
            "id": row.get("id"),
            "brand": row.get("brand"),
            "model": row.get("model"),
            "trim_level": trim,
            "verification_status": row.get("verification_status"),
            "synthesis_data": synthesis,
        }

    try:
        return _fetch(supabase_client)
    except (HttpcoreRemoteProtocolError, HttpxRemoteProtocolError) as conn_err:
        # HTTP/2 connection was dropped by Supabase (happens after hours of uptime).
        # Retry once with a fresh client before giving up.
        logger.warning(
            "HTTP/2 Server disconnected for %s — retrying with fresh client. err=%s",
            vehicle_id,
            conn_err,
        )
        try:
            return _fetch(get_fresh_client())
        except (HttpcoreRemoteProtocolError, HttpxRemoteProtocolError) as retry_err:
            raise HTTPException(
                status_code=503,
                detail=f"Supabase connection unavailable after retry: {retry_err}",
            ) from retry_err
    except HTTPException:
        raise
    except Exception as e:
        # Log full traceback server-side (logs are private), but never leak
        # internal paths/function names to clients — return a generic message.
        logger.exception(
            "Unexpected error in get_vehicle_synthesis for %s: %s", vehicle_id, e
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/extract/{vehicle_id}/markdown")
def get_vehicle_markdown(vehicle_id: str) -> Dict[str, Any]:
    """Fetch the raw markdown for a vehicle synthesis record."""
    try:
        response = (
            supabase_client.table("vehicle_synthesis")
            .select("document_markdown")
            .eq("id", vehicle_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return {"markdown": response.data[0].get("document_markdown") or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FeedbackRequest(BaseModel):
    vehicle_id: str
    brand: str
    model: str
    field_name: str
    old_value: str | None
    new_value: str | None
    context_notes: str | None = None


@router.post("/extract/feedback")
def extract_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    """Zapisuje poprawki manualne użytkownika naniesione w formularzu do tabeli extraction_corrections."""
    try:
        supabase_client.table("extraction_corrections").insert(
            {
                "vehicle_id": req.vehicle_id,
                "brand": req.brand,
                "model": req.model,
                "field_name": req.field_name,
                "old_value": req.old_value,
                "new_value": req.new_value,
                "context_notes": req.context_notes,
            }
        ).execute()
        return {"status": "success"}
    except Exception as e:
        print(f"Error saving extraction feedback: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save feedback: {str(e)}"
        )
