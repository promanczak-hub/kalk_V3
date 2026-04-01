from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, cast
from core.database import supabase

router = APIRouter(tags=["Admin Insurance"])

# --- Models: ltr_admin_ubezpieczenia ---


class InsuranceRate(BaseModel):
    id: Optional[str] = None
    klasa_samar_fk: int
    rok: int
    stawka_bazowa_ac: float
    skladka_oc_zl: float
    wsp_sredni_przebieg: Optional[float] = None
    wsp_wartosc_szkody: Optional[float] = None


# --- Models: ltr_admin_wspolczynniki_szkodowe ---


class DamageCoefficient(BaseModel):
    id: Optional[int] = None
    samar_class_id: int
    WspSredniPrzebieg: float
    WspWartoscSzkody: float


# --- Endpoints: Insurance Rates ---


@router.get("/admin/insurance-rates", response_model=List[InsuranceRate])
def get_insurance_rates(samar_class_id: Optional[int] = None):
    try:
        query = supabase.table("ltr_admin_ubezpieczenia").select("*")
        if samar_class_id is not None:
            query = query.eq("klasa_samar_fk", samar_class_id)
        response = query.order("klasa_samar_fk").order("rok").execute()
        response_data = cast(Any, response.data)
        return [InsuranceRate(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/insurance-rates", response_model=InsuranceRate)
def upsert_insurance_rate(rate: InsuranceRate):
    try:
        data = rate.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("ltr_admin_ubezpieczenia").upsert(data).execute()
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to upsert insurance rate"
            )
        response_data = cast(Any, response.data[0])
        return InsuranceRate(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/insurance-rates/bulk")
def bulk_upsert_insurance_rates(rates: List[InsuranceRate]):
    try:
        data_list = []
        for rate in rates:
            d = rate.model_dump(exclude_unset=True)
            if not d.get("id"):
                d.pop("id", None)
            data_list.append(d)
        response = supabase.table("ltr_admin_ubezpieczenia").upsert(data_list).execute()
        return {"status": "success", "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/insurance-rates/{rate_id}")
def delete_insurance_rate(rate_id: str):
    try:
        supabase.table("ltr_admin_ubezpieczenia").delete().eq("id", rate_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints: Damage Coefficients ---


@router.get("/admin/damage-coefficients", response_model=List[DamageCoefficient])
def get_damage_coefficients(samar_class_id: Optional[int] = None):
    try:
        query = supabase.table("ltr_admin_wspolczynniki_szkodowe").select("*")
        if samar_class_id is not None:
            query = query.eq("samar_class_id", samar_class_id)
        response = query.order("samar_class_id").execute()
        response_data = cast(Any, response.data)
        return [DamageCoefficient(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/damage-coefficients", response_model=DamageCoefficient)
def upsert_damage_coefficient(coeff: DamageCoefficient):
    try:
        data = coeff.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = (
            supabase.table("ltr_admin_wspolczynniki_szkodowe").upsert(data).execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to upsert damage coefficient"
            )
        response_data = cast(Any, response.data[0])
        return DamageCoefficient(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/damage-coefficients/{coeff_id}")
def delete_damage_coefficient(coeff_id: int):
    try:
        supabase.table("ltr_admin_wspolczynniki_szkodowe").delete().eq(
            "id", coeff_id
        ).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
