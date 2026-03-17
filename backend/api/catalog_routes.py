"""API routes for Catalog Library (Biblioteka Cenników).

Endpoints under /api/catalogs/...
Manages global document sources (catalogs, price lists) per brand/model.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks
from pydantic import BaseModel

from core.database import supabase as sb_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalogs", tags=["catalogs"])

# ── Constants ────────────────────────────────────────────────────
_ALLOWED_FILE_TYPES = {"pdf", "xlsx", "csv"}
_STORAGE_BUCKET = "catalog-documents"
_SERVICE_ROLE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0"
    ".EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
)


# ── Pydantic models ─────────────────────────────────────────────


class CatalogListItem(BaseModel):
    """Summary for catalog list view."""

    id: str
    brand: str
    model_family: str
    document_type: str
    display_name: str
    version_tag: Optional[str] = None
    is_active: bool
    file_type: str
    original_filename: Optional[str] = None
    extraction_status: str
    variant_count: int
    uploaded_at: str


class CatalogDetail(CatalogListItem):
    """Full catalog detail including extracted data."""

    extracted_data: Optional[dict[str, Any]] = None
    extraction_error: Optional[str] = None
    extracted_at: Optional[str] = None
    file_size_bytes: Optional[int] = None
    storage_path: str


# ── Helpers ──────────────────────────────────────────────────────


def _rs():
    """Shortcut for reverse_search schema client."""
    return sb_client.schema("reverse_search")


def _detect_file_type(filename: str) -> str:
    """Detect file type from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in _ALLOWED_FILE_TYPES:
        return ext
    raise ValueError(f"Unsupported file type: .{ext}")


# ── LIST ─────────────────────────────────────────────────────────


@router.get("")
async def list_catalogs(
    brand: Optional[str] = None,
    model_family: Optional[str] = None,
    document_type: Optional[str] = None,
) -> dict[str, Any]:
    """List all catalogs with optional filters."""
    query = (
        _rs()
        .table("model_document_sources")
        .select(
            "id, brand, model_family, document_type, "
            "display_name, version_tag, is_active, file_type, "
            "original_filename, extraction_status, variant_count, "
            "uploaded_at"
        )
        .order("uploaded_at", desc=True)
    )

    if brand:
        query = query.ilike("brand", f"%{brand}%")
    if model_family:
        query = query.ilike("model_family", f"%{model_family}%")
    if document_type:
        query = query.eq("document_type", document_type)

    resp = query.execute()
    return {"catalogs": resp.data or [], "total": len(resp.data or [])}


@router.get("/suggest")
async def suggest_catalogs(vehicle_id: str) -> dict[str, Any]:
    """Suggest best catalogs for a given vehicle using LLM ranking."""
    # 1. Fetch vehicle data
    v_resp = (
        sb_client.table("vehicle_synthesis")
        .select("synthesis_data")
        .eq("id", vehicle_id)
        .limit(1)
        .execute()
    )
    if not v_resp.data:
        raise HTTPException(404, f"Vehicle {vehicle_id} not found")

    synthesis = v_resp.data[0].get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary", {})
    if not card_summary:
        raise HTTPException(400, "Vehicle has no card_summary")

    vehicle_spec = {
        "brand": card_summary.get("brand") or synthesis.get("brand", ""),
        "model": card_summary.get("model") or synthesis.get("model", ""),
        "body_style": card_summary.get("body_style", ""),
        "powertrain": card_summary.get("powertrain", ""),
        "power_hp": card_summary.get("power_hp"),
        "drive_type": card_summary.get("drive_type", ""),
        "transmission": card_summary.get("transmission", ""),
        "vehicle_class": card_summary.get("vehicle_class", ""),
        "trim_level": card_summary.get("trim_level", ""),
        "base_price": card_summary.get("base_price") or synthesis.get("pricing", {}).get("base_price"),
    }

    # 2. Fetch all ready textual catalogs
    c_resp = (
        _rs()
        .table("model_document_sources")
        .select(
            "id, brand, model_family, document_type, display_name, version_tag, file_type, extraction_status, variant_count, extracted_data"
        )
        .eq("extraction_status", "ready")
        .order("uploaded_at", desc=True)
        .execute()
    )
    catalogs = c_resp.data or []

    if not catalogs:
        return {"catalogs": []}

    # 3. Use LLM to rank catalogs
    from core.feature_cross_reference import rank_catalogs_for_vehicle

    ranked_catalogs = rank_catalogs_for_vehicle(vehicle_spec, catalogs)

    return {"catalogs": ranked_catalogs}


# ── GET DETAIL ───────────────────────────────────────────────────


@router.get("/{catalog_id}")
async def get_catalog_detail(catalog_id: str) -> dict[str, Any]:
    """Get full catalog detail including extracted data."""
    resp = (
        _rs().table("model_document_sources").select("*").eq("id", catalog_id).execute()
    )
    if not resp.data:
        raise HTTPException(404, "Catalog not found")
    return {"catalog": resp.data[0]}


# ── UPLOAD ───────────────────────────────────────────────────────


@router.post("/upload")
async def upload_catalog(
    file: UploadFile = File(...),
    brand: str = Form(...),
    model_family: str = Form(...),
    document_type: str = Form(...),
    display_name: str = Form(...),
    version_tag: Optional[str] = Form(None),
) -> dict[str, Any]:
    """Upload a catalog/price list file and store metadata."""
    # Validate
    _VALID_DOC_TYPES = {"catalog", "price_list", "brochure", "other"}
    if document_type not in _VALID_DOC_TYPES:
        raise HTTPException(
            400,
            f"document_type must be one of: {', '.join(sorted(_VALID_DOC_TYPES))}",
        )

    filename = file.filename or "unknown"
    try:
        file_type = _detect_file_type(filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Upload to Supabase Storage
    doc_id = str(uuid.uuid4())
    storage_path = f"{brand}/{model_family}/{doc_id}.{file_type}"

    try:
        sb_client.storage.from_(_STORAGE_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={
                "content-type": file.content_type or "application/octet-stream"
            },
        )
    except Exception as exc:
        logger.error("Storage upload failed: %s", exc)
        raise HTTPException(500, f"File upload failed: {exc}") from exc

    # Insert metadata
    row = {
        "id": doc_id,
        "brand": brand.strip(),
        "model_family": model_family.strip(),
        "document_type": document_type,
        "display_name": display_name.strip(),
        "version_tag": version_tag.strip() if version_tag else None,
        "is_active": True,
        "file_type": file_type,
        "storage_path": storage_path,
        "original_filename": filename,
        "file_size_bytes": file_size,
        "extraction_status": "pending",
        "variant_count": 0,
    }

    try:
        resp = _rs().table("model_document_sources").insert(row).execute()
    except Exception as exc:
        logger.error("DB insert failed: %s", exc)
        raise HTTPException(500, f"Metadata insert failed: {exc}") from exc

    logger.info(
        "Uploaded catalog: %s (%s/%s) → %s",
        display_name,
        brand,
        model_family,
        storage_path,
    )

    return {"status": "uploaded", "catalog": resp.data[0] if resp.data else row}


# ── MARKDOWN PREVIEW ────────────────────────────────────────────


@router.get("/{catalog_id}/markdown")
async def get_catalog_markdown(catalog_id: str) -> dict[str, Any]:
    """Fetch the raw docling markdown for a catalog document."""
    resp = (
        _rs()
        .table("model_document_sources")
        .select("document_markdown")
        .eq("id", catalog_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Catalog not found")
    return {"markdown": resp.data[0].get("document_markdown") or ""}


# ── FILE DOWNLOAD / PREVIEW ─────────────────────────────────────


@router.get("/{catalog_id}/file")
async def get_catalog_file(catalog_id: str):
    """Download the original catalog file for preview."""
    resp = (
        _rs()
        .table("model_document_sources")
        .select("storage_path, file_type, original_filename")
        .eq("id", catalog_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Catalog not found")

    row = resp.data[0]
    storage_path = row["storage_path"]

    try:
        file_bytes = sb_client.storage.from_(_STORAGE_BUCKET).download(storage_path)
    except Exception as exc:
        raise HTTPException(500, f"File download failed: {exc}") from exc

    from fastapi.responses import Response

    content_type_map = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
    }
    content_type = content_type_map.get(row["file_type"], "application/octet-stream")
    filename = row.get("original_filename") or f"catalog.{row['file_type']}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ── XLSX DATA (for full viewer) ──────────────────────────────────


@router.get("/{catalog_id}/xlsx-data")
async def get_catalog_xlsx_data(catalog_id: str) -> dict[str, Any]:
    """Parse XLSX and return sheet data for frontend viewer.

    Returns all sheets with cell values, styles (colors), and metadata.
    """
    resp = (
        _rs()
        .table("model_document_sources")
        .select("storage_path, file_type")
        .eq("id", catalog_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Catalog not found")

    row = resp.data[0]
    if row["file_type"] != "xlsx":
        raise HTTPException(400, "Only XLSX files can be previewed as spreadsheet")

    try:
        file_bytes = sb_client.storage.from_(_STORAGE_BUCKET).download(
            row["storage_path"]
        )
    except Exception as exc:
        raise HTTPException(500, f"File download failed: {exc}") from exc

    from core.catalog_xlsx_parser import parse_xlsx_for_viewer

    sheets = parse_xlsx_for_viewer(file_bytes)
    return {"sheets": sheets}


# ── TRIGGER EXTRACTION ───────────────────────────────────────────


@router.post("/{catalog_id}/extract")
async def trigger_extraction(catalog_id: str) -> dict[str, Any]:
    """Trigger AI extraction of variants from catalog document."""
    resp = (
        _rs().table("model_document_sources").select("*").eq("id", catalog_id).execute()
    )
    if not resp.data:
        raise HTTPException(404, "Catalog not found")

    catalog = resp.data[0]

    if catalog["extraction_status"] == "extracting":
        raise HTTPException(409, "Extraction already in progress")

    # Mark as extracting
    _rs().table("model_document_sources").update(
        {"extraction_status": "extracting"}
    ).eq("id", catalog_id).execute()

    # Run extraction (async in background)
    import threading

    from core.catalog_extractor import extract_catalog_variants

    def _run():
        try:
            result = extract_catalog_variants(catalog)
            _rs().table("model_document_sources").update(
                {
                    "extraction_status": "ready",
                    "extracted_data": result["extracted_data"],
                    "variant_count": result["variant_count"],
                    "extracted_at": "now()",
                    "extraction_error": None,
                }
            ).eq("id", catalog_id).execute()
            logger.info(
                "Extraction complete for %s: %d variants",
                catalog["display_name"],
                result["variant_count"],
            )
        except Exception as exc:
            logger.error("Extraction failed for %s: %s", catalog_id, exc)
            _rs().table("model_document_sources").update(
                {
                    "extraction_status": "error",
                    "extraction_error": str(exc),
                }
            ).eq("id", catalog_id).execute()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"status": "extraction_started", "catalog_id": catalog_id}


# ── REPROCESS AS OFFER ──────────────────────────────────────────

@router.post("/{catalog_id}/reprocess")
async def reprocess_catalog_as_offer(
    catalog_id: str, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """Reprocess a catalog document as an OFFER."""
    resp = (
        _rs()
        .table("model_document_sources")
        .select("storage_path, original_filename, file_type")
        .eq("id", catalog_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Catalog not found")
        
    row = resp.data[0]
    storage_path = row["storage_path"]
    filename = row.get("original_filename") or f"document.{row['file_type']}"

    try:
        file_bytes = sb_client.storage.from_(_STORAGE_BUCKET).download(storage_path)
    except Exception as exc:
        raise HTTPException(500, f"File download failed: {exc}") from exc
        
    import hashlib
    md5_hash = hashlib.md5(file_bytes).hexdigest()

    content_type_map = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
    }
    mime_type = content_type_map.get(row["file_type"], "application/octet-stream")

    from core.background_jobs import process_and_save_document_bg
    
    # We create a new synthesis row for the file upload (like the regular upload does)
    new_id = str(uuid.uuid4())
    sb_client.table("vehicle_synthesis").insert({
        "id": new_id,
        "verification_status": "processing",
        "file_hash": md5_hash
    }).execute()

    background_tasks.add_task(
        process_and_save_document_bg,
        file_id=new_id,
        file_bytes=file_bytes,
        file_name=filename,
        mime_type=mime_type,
        md5_hash=md5_hash,
        force_doc_type="OFFER",  # Force processing as OFFER
    )

    # Optional: Delete the original from model_document_sources
    # Delete from DB (cascade deletes vehicle_catalog_matches)
    _rs().table("model_document_sources").delete().eq("id", catalog_id).execute()
    try:
        sb_client.storage.from_(_STORAGE_BUCKET).remove([storage_path])
    except Exception as exc:
        logger.warning("Storage delete failed (continuing): %s", exc)

    return {"status": "processing", "vehicle_id": new_id, "message": "Rozpoczęto przetwarzanie jako Oferta."}

# ── ACTIVATE / DEACTIVATE ───────────────────────────────────────


@router.patch("/{catalog_id}/activate")
async def toggle_catalog_active(
    catalog_id: str,
    is_active: bool = True,
) -> dict[str, Any]:
    """Set a catalog version as active or inactive."""
    resp = (
        _rs()
        .table("model_document_sources")
        .update({"is_active": is_active})
        .eq("id", catalog_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Catalog not found")
    return {"status": "updated", "catalog": resp.data[0]}


# ── DELETE ───────────────────────────────────────────────────────


@router.delete("/{catalog_id}")
async def delete_catalog(catalog_id: str) -> dict[str, Any]:
    """Delete a catalog and its file from storage."""
    resp = (
        _rs()
        .table("model_document_sources")
        .select("storage_path")
        .eq("id", catalog_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Catalog not found")

    storage_path = resp.data[0]["storage_path"]

    # Delete from storage
    try:
        sb_client.storage.from_(_STORAGE_BUCKET).remove([storage_path])
    except Exception as exc:
        logger.warning("Storage delete failed (continuing): %s", exc)

    # Delete from DB (cascade deletes vehicle_catalog_matches)
    _rs().table("model_document_sources").delete().eq("id", catalog_id).execute()

    return {"status": "deleted", "catalog_id": catalog_id}
