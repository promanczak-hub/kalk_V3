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
        # Fetch samar_classes to map IDs to Names
        class_res = supabase.table("samar_classes").select("id, name").execute()
        class_map = (
            {c["id"]: c["name"] for c in class_res.data} if class_res.data else {}
        )

        response = (
            supabase.table("tab_okres_final")
            .select("*")
            .order("klasa_samar")
            .order("rodzaj_silnika")
            .execute()
        )

        mapped_data = []
        for row in response.data:
            klasa_id = row.get("klasa_samar")
            mapped_data.append(
                {
                    "id": row["id"],
                    "samar_class": class_map.get(klasa_id, str(klasa_id)),
                    "engine_type": row.get("rodzaj_silnika", ""),
                    "samar_class_id": klasa_id,
                    "fuel_type_id": None,
                    "year_0": 0.0,
                    "year_1": row.get("km_35000", 0.0),
                    "year_2": row.get("km_70000", 0.0),
                    "year_3": row.get("km_105000", 0.0),
                    "year_4": row.get("km_140000", 0.0),
                    "year_5": row.get("km_175000", 0.0),
                    "year_6": row.get("km_210000", 0.0),
                    "year_7": row.get("km_245000", 0.0),
                }
            )
        return mapped_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tab-okres-final", response_model=TabOkresFinalSchema)
def create_okres_final(item: TabOkresFinalCreate):
    try:
        data = item.model_dump()
        db_payload = {
            "klasa_samar": data.get("samar_class_id", int(data.get("samar_class", 1))),
            "rodzaj_silnika": data.get("engine_type", ""),
            "km_35000": data.get("year_1", 0.0),
            "km_70000": data.get("year_2", 0.0),
            "km_105000": data.get("year_3", 0.0),
            "km_140000": data.get("year_4", 0.0),
            "km_175000": data.get("year_5", 0.0),
            "km_210000": data.get("year_6", 0.0),
            "km_245000": data.get("year_7", 0.0),
        }
        res = supabase.table("tab_okres_final").insert(db_payload).execute()
        if not res.data:
            raise HTTPException(status_code=400, detail="Failed to create record")

        return {**data, "id": res.data[0]["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tab-okres-final/{item_id}", response_model=TabOkresFinalSchema)
def update_okres_final(item_id: uuid.UUID, item: TabOkresFinalUpdate):
    try:
        db_payload = {
            "km_35000": item.year_1,
            "km_70000": item.year_2,
            "km_105000": item.year_3,
            "km_140000": item.year_4,
            "km_175000": item.year_5,
            "km_210000": item.year_6,
            "km_245000": item.year_7,
        }
        res = (
            supabase.table("tab_okres_final")
            .update(db_payload)
            .eq("id", str(item_id))
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Record not found")

        return {**item.model_dump(), "id": item_id}
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
