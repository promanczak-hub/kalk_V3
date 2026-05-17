import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import supabase

router = APIRouter(tags=["Body Types"])
logger = logging.getLogger(__name__)


class BodyTypeSchema(BaseModel):
    id: Optional[int] = None
    nazwa_nadwozia: str
    typ_pojazdu: str
    utrata_wartosci: float = 0.0
    created_at: Optional[str] = None


@router.get("/body-types", response_model=List[BodyTypeSchema])
def get_body_types():
    try:
        res = supabase.table("body_types").select("*").order("nazwa_nadwozia").execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error fetching body types: {e}")
        # Return clearer error details to help with diagnostics
        raise HTTPException(status_code=500, detail=f"Database fetch error: {str(e)}")


@router.post("/body-types", response_model=BodyTypeSchema)
def upsert_body_type(bt: BodyTypeSchema):
    try:
        data: Dict[str, Any] = {
            "nazwa_nadwozia": bt.nazwa_nadwozia,
            "typ_pojazdu": bt.typ_pojazdu,
        }
        if bt.id:
            data["id"] = bt.id
            res = supabase.table("body_types").upsert(data).execute()
        else:
            res = supabase.table("body_types").insert(data).execute()

        if not res.data:
            raise ValueError("No data returned")
        return res.data[0]
    except Exception as e:
        logger.error(f"Error saving body type: {e}")
        raise HTTPException(status_code=500, detail="Database save error")


@router.delete("/body-types/{bt_id}")
def delete_body_type(bt_id: int):
    try:
        supabase.table("body_types").delete().eq("id", bt_id).execute()
        return {"status": "ok", "deleted": True}
    except Exception as e:
        logger.error(f"Error deleting body type: {e}")
        raise HTTPException(status_code=500, detail="Database delete error")
