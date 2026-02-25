from typing import Any, Dict, List, Optional, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.samar_rv_routes import router as samar_rv_router
from core.database import supabase

app = FastAPI(title="Kalkulator LTR V2 Engine", version="1.0.0")
app.include_router(samar_rv_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GridVariant(BaseModel):
    months: List[int] = Field(
        default=[24, 36, 48, 60], description="Lista miesięcy kontraktu"
    )
    km_per_year: List[int] = Field(
        default=[10000, 20000, 30000, 40000, 50000, 60000],
        description="Opcje przebiegów rocznych",
    )


class CalculationSettings(BaseModel):
    settings_version_id: Optional[str] = Field(
        None, description="Id aktywnej wersji ustawień w DB"
    )
    overrides: Optional[Dict[str, Any]] = Field(
        None, description="Słownik nadpisań Manager'a dla wyceny (Calculation Override)"
    )


class VehicleOptions(BaseModel):
    name: str
    price_net: float
    price_gross: float
    no_discount: bool = False


class CalculatorInput(BaseModel):
    calculation_id: Optional[str] = None
    vehicle_id: str = Field(..., description="ID Auta ze słownika Supabase / SAMAR")
    base_price_net: float = Field(
        ..., description="Cena cennikowa netto wybranego pojazdu"
    )
    discount_pct: float = Field(default=0.0, description="Rabat jako procent")
    factory_options: List[VehicleOptions] = Field(default_factory=list)
    service_options: List[VehicleOptions] = Field(default_factory=list)
    grid: GridVariant = Field(default_factory=lambda: GridVariant())
    pricing_margin_pct: float = Field(
        default=0.0, description="Marża z poziomu UI (preset/suwak)"
    )
    settings: CalculationSettings = Field(
        default_factory=lambda: CalculationSettings(
            settings_version_id=None, overrides=None
        )
    )
    # Flagi dla logiki opon:
    all_season_tires: bool = Field(
        default=False, description="Opony wielosezonowe (True) czy sezonowe (False)"
    )
    tire_buyback: bool = Field(
        default=True, description="Odkup Opon na koniec kontraktu"
    )

    # Podatki i Finanse (PMT)
    wibor_pct: float = Field(default=5.0, description="WIBOR %")
    margin_pct: float = Field(default=2.0, description="Marża Finansowa Leasingu %")
    initial_deposit_pct: float = Field(
        default=0.0, description="Oplata Wstępna (Czynsz Inicjalny) % z ceny auta"
    )

    # Samochód Zastępczy
    replacement_car_enabled: bool = Field(
        default=True, description="Czy wliczać koszty auta zastępczego"
    )

    # Koszty Dodatkowe
    add_gsm_subscription: bool = Field(default=True, description="Abonament GSM")
    add_hook_installation: bool = Field(default=False, description="Montaż Haka")
    add_grid_dismantling: bool = Field(default=False, description="Wymontowanie Kraty")
    add_registration: bool = Field(default=True, description="Rejestracja")
    add_sales_prep: bool = Field(default=True, description="Przygotowanie do sprzedaży")


class ControlCenterSettings(BaseModel):
    default_wibor: float
    default_ltr_margin: float
    bank_spread: float
    samar_segment_b_adjustment: int
    samar_segment_c_adjustment: int
    samar_segment_d_adjustment: int
    value_threshold_1: float
    value_threshold_2: float
    resale_time_days: int
    inventory_financing_cost: float
    samar_rv_apply_color_correction: bool
    samar_rv_apply_body_correction: bool
    samar_rv_apply_options_depreciation: bool
    samar_rv_base_mileage: int
    samar_rv_mileage_unit_km: int

    # Koszty Dodatkowe
    cost_gsm_subscription_monthly: float
    cost_gsm_device: float
    cost_gsm_installation: float
    cost_hook_installation: float
    cost_grid_dismantling: float
    cost_registration: float
    cost_sales_prep: float


class TyreCost(BaseModel):
    id: Optional[str] = None
    tyre_class: str
    diameter: int
    purchase_price: float
    buyback_price: float


class ServiceRate(BaseModel):
    id: Optional[int] = None
    klasa_id: int
    rodzaj_paliwa: str
    stawka_za_km: float


class ServiceBaseCost(BaseModel):
    id: Optional[int] = None
    klasa_id: int
    koszt_przegladu_podstawowego: float


@app.get("/api/control-center", tags=["Control Center"])
async def get_control_center() -> ControlCenterSettings:
    try:
        response = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Control center settings not found"
            )
        response_data = cast(Any, response.data[0])
        return ControlCenterSettings(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/control-center", tags=["Control Center"])
async def update_control_center(
    settings: ControlCenterSettings,
) -> ControlCenterSettings:
    try:
        data = settings.model_dump()
        data["id"] = 1
        response = supabase.table("control_center").update(data).eq("id", 1).execute()

        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to update control center settings"
            )

        response_data = cast(Any, response.data[0])
        return ControlCenterSettings(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tyre-costs", tags=["Control Center"])
async def get_tyre_costs() -> List[TyreCost]:
    try:
        response = (
            supabase.table("tyre_costs").select("*").order("tyre_class").execute()
        )
        response_data = cast(Any, response.data)
        return [TyreCost(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tyre-costs", tags=["Control Center"])
async def update_tyre_cost(cost: TyreCost) -> TyreCost:
    try:
        data = cost.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("tyre_costs").upsert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update tyre cost")
        response_data = cast(Any, response.data[0])
        return TyreCost(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/tyre-costs/{cost_id}", tags=["Control Center"])
async def delete_tyre_cost(cost_id: str) -> Dict[str, str]:
    try:
        supabase.table("tyre_costs").delete().eq("id", cost_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/service-rates", tags=["Control Center"])
async def get_service_rates() -> List[ServiceRate]:
    try:
        response = (
            supabase.table("service_rates_config")
            .select("*")
            .order("klasa_id")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [ServiceRate(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/service-rates", tags=["Control Center"])
async def update_service_rate(rate: ServiceRate) -> ServiceRate:
    try:
        data = rate.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("service_rates_config").upsert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update service rate")
        response_data = cast(Any, response.data[0])
        return ServiceRate(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/service-rates/{rate_id}", tags=["Control Center"])
async def delete_service_rate(rate_id: int) -> Dict[str, str]:
    try:
        supabase.table("service_rates_config").delete().eq("id", rate_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/service-base-costs", tags=["Control Center"])
async def get_service_base_costs() -> List[ServiceBaseCost]:
    try:
        response = (
            supabase.table("service_base_costs_config")
            .select("*")
            .order("klasa_id")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [ServiceBaseCost(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/service-base-costs", tags=["Control Center"])
async def update_service_base_cost(cost: ServiceBaseCost) -> ServiceBaseCost:
    try:
        data = cost.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("service_base_costs_config").upsert(data).execute()
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to update service base cost"
            )
        response_data = cast(Any, response.data[0])
        return ServiceBaseCost(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/service-base-costs/{cost_id}", tags=["Control Center"])
async def delete_service_base_cost(cost_id: int) -> Dict[str, str]:
    try:
        supabase.table("service_base_costs_config").delete().eq("id", cost_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calculate-matrix")
async def calculate_matrix(data: CalculatorInput) -> Dict[str, Any]:
    try:
        from core.engine import CalculationEngine

        response = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Control center settings not found"
            )
        response_data = cast(Any, response.data[0])
        settings = ControlCenterSettings(**response_data)

        # Override frontend input with authoritative DB settings
        data.wibor_pct = settings.default_wibor
        data.margin_pct = settings.default_ltr_margin

        engine = CalculationEngine(input_data=data, settings=settings)
        matrix_cells = engine.build_matrix()
        return {
            "status": "success",
            "message": "Matrix calculation completed successfully",
            "cells": matrix_cells,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.1", port=8000)
