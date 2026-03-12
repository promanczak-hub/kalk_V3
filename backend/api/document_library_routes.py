from fastapi import APIRouter, HTTPException, BackgroundTasks
from core.database import supabase
from typing import Any, Dict
import requests
import uuid
import os
from urllib.parse import urlparse
from core.background_jobs import process_and_save_document_bg

router = APIRouter(prefix="/document-library", tags=["document_library"])


@router.get("")
async def list_documents() -> Dict[str, Any]:
    """Fetch all documents from the document_library table."""
    try:
        response = (
            supabase.table("document_library")
            .select(
                "id, created_at, file_name, document_url, document_type, brand, model, valid_from, description"
            )
            .order("created_at", desc=True)
            .execute()
        )
        return {"documents": response.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(document_id: str) -> Dict[str, Any]:
    """Fetch a single document by ID from the document_library table."""
    try:
        response = (
            supabase.table("document_library")
            .select("*")
            .eq("id", document_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"document": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/markdown")
async def get_document_markdown(document_id: str) -> Dict[str, Any]:
    """Fetch the raw markdown for a document."""
    try:
        response = (
            supabase.table("document_library")
            .select("document_markdown")
            .eq("id", document_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"markdown": response.data[0].get("document_markdown") or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> Dict[str, Any]:
    """Delete a document from the document_library table."""
    try:
        # Note: Ideally we should delete from storage as well, but document_url is stored, not storage_path.
        # We'd have to parse the URL to get the path, or just leave it in storage if it doesn't matter (since it's a raw dump).
        supabase.table("document_library").delete().eq("id", document_id).execute()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Fetch a document from the library and re-send it to the background processor
    as a forced 'OFFER' (single cars pipeline). Then delete from the library.
    """
    try:
        # 1. Fetch document from library
        response = (
            supabase.table("document_library")
            .select("*")
            .eq("id", document_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = response.data[0]
        file_name = doc.get("file_name", "document.pdf")
        document_url = doc.get("document_url")

        if not document_url:
            raise HTTPException(status_code=400, detail="Document lacks a valid URL.")

        # 2. Download the file from the URL
        print(f"[REPROCESS] Downloading {document_url}...")
        download_response = requests.get(document_url, timeout=30)
        download_response.raise_for_status()
        file_bytes = download_response.content

        # Determine MIME type based on extension
        ext = os.path.splitext(urlparse(document_url).path)[1].lower()
        _MIME_MAP = {
            ".pdf": "application/pdf",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
        }
        mime_type = _MIME_MAP.get(ext, "application/octet-stream")

        # 3. Create a new vehicle_synthesis id and record to show processing status immediately
        from core.pipeline_router import DOC_TYPE_OFFER
        
        new_file_id = str(uuid.uuid4())
        
        supabase.table("vehicle_synthesis").insert({
            "id": new_file_id,
            "verification_status": "processing",
        }).execute()
        
        # 4. Fire the background job with force_doc_type
        print(f"[REPROCESS] Starting background job for {new_file_id} via force_doc_type={DOC_TYPE_OFFER}...")
        background_tasks.add_task(
            process_and_save_document_bg,
            file_id=new_file_id,
            file_bytes=file_bytes,
            file_name=file_name,
            mime_type=mime_type,
            md5_hash="",  # We skip md5_hash check on reprocess / assume unique
            force_doc_type=DOC_TYPE_OFFER,
        )

        # 5. Remove it from the document library
        print(f"[REPROCESS] Deleting {document_id} from document_library...")
        supabase.table("document_library").delete().eq("id", document_id).execute()

        return {
            "status": "processing",
            "file_id": new_file_id,
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to download document: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
