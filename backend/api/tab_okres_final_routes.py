from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import supabase
import uuid

router = APIRouter(tags=["Tab Okres Final"])


class TabOkresFinalBase(BaseModel):
    samar_class: str
    engine_type: str
    samar_class_id: Optional[int] = None
    fuel_type_id: Optional[int] = None
    year_0: float = 0.0
    year_1: float = 0.0
    year_2: float = 0.0
    year_3: float = 0.0
    year_4: float = 0.0
    year_5: float = 0.0
    year_6: float = 0.0
    year_7: float = 0.0


class TabOkresFinalSchema(TabOkresFinalBase):
    id: uuid.UUID


class TabOkresFinalCreate(TabOkresFinalBase):
    pass


class TabOkresFinalUpdate(TabOkresFinalBase):
    pass


@router.get("/tab-okres-final", response_model=List[TabOkresFinalSchema])
def get_all_okres_final():
    try:
        response = (
            supabase.table("tab_okres_final")
            .select("*")
            .order("samar_class")
            .order("engine_type")
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tab-okres-final", response_model=TabOkresFinalSchema)
def create_okres_final(item: TabOkresFinalCreate):
    try:
        data = item.model_dump()
        response = supabase.table("tab_okres_final").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create record")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tab-okres-final/{item_id}", response_model=TabOkresFinalSchema)
def update_okres_final(item_id: uuid.UUID, item: TabOkresFinalUpdate):
    try:
        response = (
            supabase.table("tab_okres_final")
            .update(item.model_dump())
            .eq("id", str(item_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Record not found")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tab-okres-final/{item_id}")
def delete_okres_final(item_id: uuid.UUID):
    try:
        response = (
            supabase.table("tab_okres_final").delete().eq("id", str(item_id)).execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
