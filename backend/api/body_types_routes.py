import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import supabase

# Edycja SOT odbywa się w GSheet (gid=484265370) i synchronizowana jest
# do DB przez `backend/scripts/sync_body_types.py`, NIE przez HTTP API.
# Dlatego ten router ma wyłącznie GET — wcześniejsze POST/DELETE były
# osierocone (brak FE i CLI caller) i stanowiły niezautoryzowaną dziurę
# w SOT korekt WR. Usunięte 2026-05-17.

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
        raise HTTPException(status_code=500, detail=f"Database fetch error: {str(e)}")
