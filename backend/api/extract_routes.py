import json
import logging
import asyncio
from typing import Any, Dict
from pydantic import BaseModel
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
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
    """
    import psycopg2
    from psycopg2.extras import Json
    import os

    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        # Fallback: build from SUPABASE_URL
        host = SUPABASE_URL.replace("https://", "").replace("http://", "").rstrip("/")
        # Direct postgres connection to Supabase: db.{ref}.supabase.co:5432
        ref = host.split(".")[0]
        password = os.getenv("SUPABASE_DB_PASSWORD")
        if not password:
            raise RuntimeError("SUPABASE_DB_PASSWORD not set in env")
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


@router.post("/delete-vehicles-batch")
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
        import traceback

        error_msg = f"Unexpected error in get_vehicle_synthesis for {vehicle_id}: {e}"
        logger.error(error_msg, exc_info=True)
        # return full traceback in detail for easier debugging in dev
        raise HTTPException(
            status_code=500, detail=f"{error_msg}\n{traceback.format_exc()}"
        )


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
