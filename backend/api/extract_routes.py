import json
import requests
from typing import Any, Dict
from pydantic import BaseModel
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import Response
from core.extractor_v2 import process_manual_override_v2
from core.json_utils import clean_json_response
from core.background_jobs import process_and_save_document_bg
from services.ai_mapper_service import map_vehicle_data_flash

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
                "Content-Disposition": "inline",
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
