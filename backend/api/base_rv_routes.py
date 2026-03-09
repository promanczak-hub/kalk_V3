from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from core.database import supabase
from pydantic import BaseModel

router = APIRouter()


class BaseRVUpdatePayload(BaseModel):
    engine_type_id: int
    base_rv_percent: float


@router.get("/samar-class-base-rv/{samar_class_id}")
async def get_samar_class_base_rv(samar_class_id: int):
    try:
        response = (
            supabase.table("samar_class_base_rv")
            .select(
                "id, samar_class_id, engine_type_id, base_rv_percent, engines:engine_type_id(name)"
            )
            .eq("samar_class_id", samar_class_id)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/samar-class-base-rv/{samar_class_id}")
async def update_samar_class_base_rv(
    samar_class_id: int, payload: List[BaseRVUpdatePayload]
):
    try:
        for item in payload:
            (
                supabase.table("samar_class_base_rv")
                .upsert(
                    {
                        "samar_class_id": samar_class_id,
                        "engine_type_id": item.engine_type_id,
                        "base_rv_percent": item.base_rv_percent,
                    },
                    on_conflict="samar_class_id, engine_type_id",
                )
                .execute()
            )
        return {"status": "success", "message": "Updated base rv rates"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
