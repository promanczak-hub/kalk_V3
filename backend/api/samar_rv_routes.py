from typing import List, Dict, Any, cast
from fastapi import APIRouter, HTTPException
from core.database import supabase

router = APIRouter(prefix="/api/samar-rv", tags=["SamarRV"])


@router.get("/classes")
def get_samar_classes() -> List[Dict[str, Any]]:
    """Returns real SAMAR class names via samar_classes bridge table.
    Format: {id: klasa_wr_id, nazwa: samar_class_name} for backward compat."""
    try:
        sc = (
            supabase.table("samar_classes")
            .select("id,name,klasa_wr_id")
            .order("name")
            .execute()
        )
        result: List[Dict[str, Any]] = []
        for r in sc.data:
            wr_id = r.get("klasa_wr_id")
            if wr_id is not None:
                result.append({"id": wr_id, "nazwa": r["name"]})
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


@router.get("/insurance-rates")
def get_insurance_rates() -> List[Dict[str, Any]]:
    try:
        res = (
            supabase.table("ltr_admin_ubezpieczenia")
            .select("*")
            .order("KlasaId", desc=True)
            .order("KolejnyRok")
            .execute()
        )
        return cast(List[Dict[str, Any]], res.data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insurance-rates")
def update_insurance_rate(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if "id" not in data:
            raise HTTPException(status_code=400, detail="Missing id in data")

        # Remove joined data if it exists from payload before upsert
        if "samar_klasa_wr" in data:
            del data["samar_klasa_wr"]

        res = supabase.table("ltr_admin_ubezpieczenia").upsert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Modyfikacja nie powiodła się")
        return cast(Dict[str, Any], res.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insurance-coefficients")
def get_insurance_coefficients() -> List[Dict[str, Any]]:
    try:
        res = (
            supabase.table("ltr_admin_wspolczynniki_szkodowe")
            .select("*")
            .order("klasa_wr_id", desc=True)
            .execute()
        )
        return cast(List[Dict[str, Any]], res.data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insurance-coefficients")
def update_insurance_coefficient(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if "id" not in data:
            raise HTTPException(status_code=400, detail="Missing id in data")

        # Remove joined data if it exists from payload before upsert
        if "samar_klasa_wr" in data:
            del data["samar_klasa_wr"]

        res = supabase.table("ltr_admin_wspolczynniki_szkodowe").upsert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Modyfikacja nie powiodła się")
        return cast(Dict[str, Any], res.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
