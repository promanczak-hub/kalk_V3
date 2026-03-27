import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import supabase

router = APIRouter(tags=["Body Type WR Corrections"])
logger = logging.getLogger(__name__)


class BodyTypeCorrectionSchema(BaseModel):
    id: Optional[int] = None
    samar_class_id: Optional[int] = None
    engine_type_id: Optional[int] = None
    brand_name: Optional[str] = ""
    body_type_id: Optional[int] = None
    correction_percent: float = 0.0
    zabudowa_correction_percent: float = 0.0


@router.get("/body-type-wr-corrections", response_model=List[BodyTypeCorrectionSchema])
async def get_body_type_corrections():
    try:
        res = supabase.table("body_type_wr_corrections").select("*").execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error fetching body_type_wr_corrections: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")


@router.post("/body-type-wr-corrections", response_model=BodyTypeCorrectionSchema)
async def upsert_body_type_correction(btc: BodyTypeCorrectionSchema):
    try:
        data = {
            "samar_class_id": btc.samar_class_id,
            "engine_type_id": btc.engine_type_id,
            "brand_name": btc.brand_name.strip().upper() if btc.brand_name else "",
            "body_type_id": btc.body_type_id,
            "correction_percent": btc.correction_percent,
            "zabudowa_correction_percent": btc.zabudowa_correction_percent,
        }
        if btc.id:
            data["id"] = btc.id
            res = (
                supabase.table("body_type_wr_corrections")
                .update(data)
                .eq("id", btc.id)
                .execute()
            )
        else:
            res = supabase.table("body_type_wr_corrections").insert(data).execute()

        if not res.data:
            raise ValueError("No data returned")
        return res.data[0]
    except Exception as e:
        logger.error(f"Error saving body_type_wr_corrections: {e}")
        raise HTTPException(status_code=500, detail="Database save error")


@router.delete("/body-type-wr-corrections/{btc_id}")
async def delete_body_type_correction(btc_id: int):
    try:
        supabase.table("body_type_wr_corrections").delete().eq("id", btc_id).execute()
        return {"status": "ok", "deleted": True}
    except Exception as e:
        logger.error(f"Error deleting body_type_wr_corrections: {e}")
        raise HTTPException(status_code=500, detail="Database delete error")
