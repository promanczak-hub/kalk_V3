from fastapi import APIRouter, HTTPException
from core.database import supabase
from typing import Any, Dict

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
