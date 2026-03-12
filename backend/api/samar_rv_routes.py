from typing import List, Dict, Any, cast
from fastapi import APIRouter, HTTPException
from core.database import supabase

router = APIRouter(prefix="/api/samar-rv", tags=["SamarRV"])


@router.get("/classes")
def get_samar_classes() -> List[Dict[str, Any]]:
    """Returns SAMAR class list.
    Format: {id: samar_class_id, nazwa: samar_class_name}."""
    try:
        sc = supabase.table("samar_classes").select("id,name").order("name").execute()
        result: List[Dict[str, Any]] = []
        for r in sc.data or []:
            r_dict = cast(Dict[str, Any], r)
            result.append({"id": r_dict["id"], "nazwa": r_dict["name"]})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classes")
def update_samar_class(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if "id" not in data:
            raise HTTPException(status_code=400, detail="Missing id in data")
        res = supabase.table("samar_klasa_wr").upsert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to update samar class")
        return cast(Dict[str, Any], res.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/base-percentages")
def get_base_percentages() -> List[Dict[str, Any]]:
    try:
        res = (
            supabase.table("ltr_admin_tabela_wr_klasas")
            .select("*")
            .order("id")
            .execute()
        )
        return cast(List[Dict[str, Any]], res.data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brand-corrections")
def get_brand_corrections() -> List[Dict[str, Any]]:
    try:
        res = (
            supabase.table("ltr_admin_korekta_wr_markas")
            .select("*")
            .order("id")
            .execute()
        )
        return cast(List[Dict[str, Any]], res.data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/depreciation")
def get_depreciation() -> List[Dict[str, Any]]:
    try:
        res = (
            supabase.table("ltr_admin_tabela_wr_deprecjacjas")
            .select("*")
            .order("id")
            .execute()
        )
        return cast(List[Dict[str, Any]], res.data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mileage")
def get_mileage() -> List[Dict[str, Any]]:
    try:
        res = (
            supabase.table("ltr_admin_tabela_wr_przebiegs")
            .select("*")
            .order("id")
            .execute()
        )
        return cast(List[Dict[str, Any]], res.data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Placeholder POST endpoints for updates (up to the user requirements later, normally we edit existing table structure)
@router.post("/base-percentages")
def update_base_percentage(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # data needs identifier (e.g. `id`) to issue an upsert
        res = supabase.table("ltr_admin_tabela_wr_klasas").upsert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Modyfikacja nie powiodła się")
        return cast(Dict[str, Any], res.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
