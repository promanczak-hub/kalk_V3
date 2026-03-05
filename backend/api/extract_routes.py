import json
import requests
from typing import Any, Dict
from pydantic import BaseModel
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import Response
from core.extractor_v2 import process_manual_override_v2
from core.json_utils import clean_json_response
from core.background_jobs import process_and_save_document_bg, trigger_cancel
from core.pipeline_service_option import extract_service_option_from_pdf
from services.ai_mapper_service import map_vehicle_data_flash
from core.database import supabase as supabase_client

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
    # We allow pdf and excel files to be sent to Gemini
    supported_extensions = (".pdf", ".xls", ".xlsx")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    if not any(file.filename.lower().endswith(ext) for ext in supported_extensions):
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    try:
        # Read the file bytes directly from the UploadFile
        file_bytes = await file.read()
        mime_type = file.content_type or "application/pdf"

        # Route EVERY document background task
        print(f"Routing {file.filename} to universal extractor V2 (Background)")
        background_tasks.add_task(
            process_and_save_document_bg,
            file_id=file_id,
            file_bytes=file_bytes,
            file_name=file.filename,
            mime_type=mime_type,
            md5_hash="",
        )

        return {"status": "processing", "file_id": file_id}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during extraction initialization: {str(e)}",
        )


@router.post("/extract/service-option")
async def extract_service_option(
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    supported_extensions = (".pdf", ".png", ".jpg", ".jpeg", ".webp")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    if not any(file.filename.lower().endswith(ext) for ext in supported_extensions):
        raise HTTPException(
            status_code=400, detail="Unsupported file format. Use PDF or Images."
        )

    try:
        file_bytes = await file.read()
        mime_type = file.content_type or "application/pdf"

        # Synchronously call the new LLM pipeline
        print(f"Extracting Service Option from {file.filename}")
        extracted_data = extract_service_option_from_pdf(
            document_data=file_bytes, mime_type=mime_type
        )

        if not extracted_data:
            raise HTTPException(status_code=500, detail="Failed to extract data.")

        return extracted_data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during service option extraction: {str(e)}",
        )


@router.post("/extract/manual-override")
async def manual_override(request: ManualOverrideRequest) -> Dict[str, Any]:
    try:
        print(f"Processing manual override requested by user: '{request.user_prompt}'")
        updated_json_str = process_manual_override_v2(
            request.original_json, request.user_prompt
        )
        obj = json.loads(clean_json_response(updated_json_str))
        return obj  # type: ignore
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during manual override: {str(e)}",
        )


class MapDataRequest(BaseModel):
    original_json: Dict[str, Any]


@router.post("/extract/map-vehicle-data")
async def map_vehicle_data(request: MapDataRequest) -> Dict[str, Any]:
    try:
        print("Processing AI data mapping for vehicle JSON.")
        mapped_data = map_vehicle_data_flash(request.original_json)
        return mapped_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during AI data mapping: {str(e)}",
        )


@router.get("/pdf-proxy")
def proxy_pdf(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        response = requests.get(url)
        response.raise_for_status()
        return Response(
            content=response.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="document.pdf"',
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Resource-Policy": "cross-origin",
            },
        )
    except Exception as e:
        print(f"Error proxying PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to proxy PDF")


class DeleteVehicleRequest(BaseModel):
    vehicle_id: str


@router.post("/delete-vehicle")
async def delete_vehicle(request: DeleteVehicleRequest) -> Dict[str, Any]:
    from core.database import supabase

    try:
        print(f"Deleting vehicle strictly from synthesis with ID: {request.vehicle_id}")

        supabase.table("vehicle_synthesis").delete().eq(
            "id", request.vehicle_id
        ).execute()

        return {"status": "success", "message": "Vehicle deleted successfully"}
    except Exception as e:
        print(f"Error deleting vehicle: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete vehicle")


class CancelProcessingRequest(BaseModel):
    vehicle_id: str


@router.post("/cancel-processing")
async def cancel_processing(request: CancelProcessingRequest) -> Dict[str, Any]:
    """
    Immediately cancels document processing:
    1. Sets DB status to 'cancelled' → triggers Supabase Realtime → instant UI update
    2. Signals the background thread to stop before next LLM call
    """
    try:
        # 1. Immediately update DB — frontend sees this via Realtime
        supabase_client.table("vehicle_synthesis").update(
            {"verification_status": "cancelled"}
        ).eq("id", request.vehicle_id).execute()

        # 2. Signal the background thread to stop
        was_running = trigger_cancel(request.vehicle_id)

        print(
            f"[CANCEL] Vehicle {request.vehicle_id} cancelled. "
            f"Thread was {'running' if was_running else 'not found (already finished)'}"
        )

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
async def delete_vehicles_batch(request: BatchDeleteRequest) -> Dict[str, Any]:
    """Delete multiple vehicles in a single transaction."""
    if not request.vehicle_ids:
        raise HTTPException(status_code=400, detail="No vehicle IDs provided.")

    try:
        print(f"Batch deleting {len(request.vehicle_ids)} vehicles")
        supabase_client.table("vehicle_synthesis").delete().in_(
            "id", request.vehicle_ids
        ).execute()

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
async def compare_vehicles(request: CompareVehiclesRequest) -> Dict[str, Any]:
    """
    Compare 2-5 vehicles using Gemini Flash.
    Extracts key data from synthesis_data and produces a markdown comparison.
    """
    import google.generativeai as genai

    if len(request.vehicle_ids) < 2:
        raise HTTPException(status_code=400, detail="Minimum 2 vehicles required.")
    if len(request.vehicle_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 vehicles.")

    try:
        # Fetch vehicles
        result = (
            supabase_client.table("vehicle_synthesis")
            .select("id, brand, model, trim_level, synthesis_data")
            .in_("id", request.vehicle_ids)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Vehicles not found.")

        # Build comparison payloads
        vehicle_payloads = []
        for row in result.data:
            name = f"{row.get('brand', '?')} {row.get('model', '')} {row.get('trim_level', '')}".strip()
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

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

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
