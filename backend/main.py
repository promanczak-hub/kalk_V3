from typing import Any, Dict, List, Optional, cast

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.samar_rv_routes import router as samar_rv_router
from api.parser_routes import router as parser_router
from api.kalkulacje_routes import router as kalkulacje_router
from api.budget_finder_routes import router as budget_finder_router
from api.calculator_excel_data_routes import router as calculator_excel_data_router
from api.extract_routes import router as extract_router
from api.homologation_routes import router as homologation_router
from core.database import supabase
import pandas as pd
import io

app = FastAPI(title="Kalkulator LTR V2 Engine", version="1.0.0")
app.include_router(samar_rv_router)
app.include_router(parser_router, prefix="/api")
app.include_router(extract_router, prefix="/api")
app.include_router(kalkulacje_router, prefix="/api")
app.include_router(budget_finder_router, prefix="/api")  # type: ignore
app.include_router(calculator_excel_data_router, prefix="/api")
app.include_router(homologation_router, prefix="/api")

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
    include_in_wr: bool = False


class CalculatorInput(BaseModel):
    calculation_id: Optional[str] = None
    vehicle_id: str = Field(..., description="ID Auta ze słownika Supabase / SAMAR")
    base_price_net: float = Field(
        ..., description="Cena cennikowa netto wybranego pojazdu"
    )
    discount_pct: float = Field(default=0.0, description="Rabat jako procent")
    factory_options: List[VehicleOptions] = Field(default_factory=list)
    service_options: List[VehicleOptions] = Field(default_factory=list)
    # Parametry bazowe (Siatka Dynamiczna V3)
    okres_bazowy: int = Field(
        default=48, description="Domyślny/bazowy okres w miesiącach z Card Summary"
    )
    przebieg_bazowy: int = Field(
        default=140000, description="Domyślny/bazowy przebieg z Card Summary"
    )

    pricing_margin_pct: float = Field(
        default=0.0, description="Marża z poziomu UI (preset/suwak)"
    )
    settings: CalculationSettings = Field(
        default_factory=lambda: CalculationSettings(
            settings_version_id=None, overrides=None
        )
    )
    # Flagi dla logiki opon:
    z_oponami: bool = Field(default=True, description="Czy z oponami")
    klasa_opony_string: str = Field(
        default="Medium", description="Klasa Opon np. 'WIELOSEZONOWE MEDIUM'"
    )
    korekta_kosztu_opon: bool = Field(
        default=False, description="Czy stosować ręczną korektę"
    )
    koszt_opon_korekta: float = Field(default=0.0, description="Kwota korekty brutto")
    liczba_kompletow_opon: Optional[float] = Field(
        default=None, description="Ręczna liczba kompletów (opcjonalna)"
    )
    srednica_felgi: Optional[int] = Field(
        default=None,
        description="Średnica felgi w calach (z plakietki pojazdu). Wymagana gdy z_oponami=True.",
    )

    # Podatki i Finanse (PMT)
    wibor_pct: float = Field(default=5.0, description="WIBOR %")
    margin_pct: float = Field(default=2.0, description="Marża Finansowa Leasingu %")
    depreciation_pct: Optional[float] = Field(
        default=None,
        description="Procent amortyzacji przekazany z UI (nadpisuje dynamikę SAMAR)",
    )
    manual_wr_correction: float = Field(
        default=0.0,
        description="Ręczna korekta kwotowa (netto) Wartości Rezydualnej przekazywana z UI",
    )
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

    # Nowe pola V1→V3
    service_cost_type: str = Field(
        default="ASO",
        description="Rodzaj kosztów serwisowych: 'ASO' lub 'nonASO'",
    )
    pakiet_serwisowy: float = Field(
        default=0.0,
        description=(
            "Dedykowany pakiet serwisowy netto na kontrakt. "
            "Jeśli > 0, zastępuje logikę km-ową."
        ),
    )
    inne_koszty_serwisowania_netto: float = Field(
        default=0.0,
        description="Dodatkowe koszty serwisowania netto MIESIĘCZNIE.",
    )
    vehicle_vintage: str = Field(
        default="current",
        description="Rocznik pojazdu: 'current' (bieżący) lub 'previous' (ubiegły)",
    )
    is_metalic: bool = Field(
        default=False,
        description="Czy lakier metalik/perłowy (wpływa na korektę WR)",
    )


from core.models import ControlCenterSettings  # noqa: E402


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


class EngineType(BaseModel):
    id: Optional[int] = None
    name: str
    category: str
    description: Optional[str] = None


class SamarClass(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    mileage_cutoff_threshold: Optional[int] = None
    example_models: Optional[str] = None


class SamarServiceCost(BaseModel):
    id: Optional[str] = None
    samar_class_id: int
    engine_type_id: int
    power_band: str
    cost_aso_per_km: float
    cost_non_aso_per_km: float


class ReplacementCarRate(BaseModel):
    id: Optional[str] = None
    samar_class_id: int
    samar_class_name: str = ""
    average_days_per_year: float = 6.5
    daily_rate_net: float


class BrandCorrection(BaseModel):
    id: Optional[str] = None
    klasa_samar: str
    rodzaj_paliwa: str
    marka: str
    correction_percent: float


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


@app.get("/api/engines", tags=["Control Center"])
async def get_engines() -> List[EngineType]:
    try:
        response = (
            supabase.table("engines")
            .select("*")
            .order("category")
            .order("name")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [EngineType(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/engines", tags=["Control Center"])
async def update_engine(engine: EngineType) -> EngineType:
    try:
        data = engine.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("engines").upsert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update engine")
        response_data = cast(Any, response.data[0])
        return EngineType(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/engines/{engine_id}", tags=["Control Center"])
async def delete_engine(engine_id: int) -> Dict[str, str]:
    try:
        supabase.table("engines").delete().eq("id", engine_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Depreciation Rates (per engine × samar_class × year) ---


class DepreciationRate(BaseModel):
    id: Optional[int] = None
    samar_class_id: int
    fuel_type_id: int  # references engines.id (1:1)
    year: int
    base_depreciation_percent: float = 0.0
    options_depreciation_percent: float = 0.0


@app.get("/api/depreciation-rates", tags=["Control Center"])
async def get_depreciation_rates(
    samar_class_id: Optional[int] = None,
) -> List[DepreciationRate]:
    try:
        query = supabase.table("samar_class_depreciation_rates").select("*")
        if samar_class_id is not None:
            query = query.eq("samar_class_id", samar_class_id)
        response = (
            query.order("samar_class_id").order("fuel_type_id").order("year").execute()
        )
        response_data = cast(Any, response.data)
        return [DepreciationRate(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/depreciation-rates", tags=["Control Center"])
async def upsert_depreciation_rate(rate: DepreciationRate) -> DepreciationRate:
    try:
        data = rate.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = (
            supabase.table("samar_class_depreciation_rates").upsert(data).execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to upsert rate")
        response_data = cast(Any, response.data[0])
        return DepreciationRate(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/depreciation-rates/bulk", tags=["Control Center"])
async def bulk_upsert_depreciation_rates(
    rates: List[DepreciationRate],
) -> Dict[str, Any]:
    try:
        data_list = []
        for rate in rates:
            d = rate.model_dump(exclude_unset=True)
            if not d.get("id"):
                d.pop("id", None)
            data_list.append(d)
        response = (
            supabase.table("samar_class_depreciation_rates").upsert(data_list).execute()
        )
        return {"status": "success", "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/depreciation-rates/{rate_id}", tags=["Control Center"])
async def delete_depreciation_rate(rate_id: int) -> Dict[str, str]:
    try:
        supabase.table("samar_class_depreciation_rates").delete().eq(
            "id", rate_id
        ).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Mileage Corrections (per engine × samar_class) ---


class MileageCorrection(BaseModel):
    id: Optional[int] = None
    samar_class_id: int
    fuel_type_id: int  # references engines.id (1:1)
    under_threshold_percent: float = 0.0
    over_threshold_percent: float = 0.0


@app.get("/api/mileage-corrections", tags=["Control Center"])
async def get_mileage_corrections(
    samar_class_id: Optional[int] = None,
) -> List[MileageCorrection]:
    try:
        query = supabase.table("samar_class_mileage_corrections").select("*")
        if samar_class_id is not None:
            query = query.eq("samar_class_id", samar_class_id)
        response = query.order("samar_class_id").order("fuel_type_id").execute()
        response_data = cast(Any, response.data)
        return [MileageCorrection(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mileage-corrections/bulk", tags=["Control Center"])
async def bulk_upsert_mileage_corrections(
    corrections: List[MileageCorrection],
) -> Dict[str, Any]:
    try:
        data_list = []
        for c in corrections:
            d = c.model_dump(exclude_unset=True)
            if not d.get("id"):
                d.pop("id", None)
            data_list.append(d)
        response = (
            supabase.table("samar_class_mileage_corrections")
            .upsert(data_list)
            .execute()
        )
        return {"status": "success", "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/mileage-corrections/{correction_id}", tags=["Control Center"])
async def delete_mileage_correction(correction_id: int) -> Dict[str, str]:
    try:
        supabase.table("samar_class_mileage_corrections").delete().eq(
            "id", correction_id
        ).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/samar-classes", tags=["Control Center"])
async def get_samar_classes() -> List[SamarClass]:
    try:
        response = supabase.table("samar_classes").select("*").order("id").execute()
        response_data = cast(Any, response.data)

        # Fetch example models from KlasaSAMAR_czak mapping
        try:
            samar_czak = (
                supabase.table("KlasaSAMAR_czak").select("col_1", "col_8").execute()
            )
            czak_data = cast(Any, samar_czak.data)
            czak_mapping = {
                row.get("col_1"): row.get("col_8")
                for row in czak_data
                if row.get("col_1")
            }
        except Exception:
            czak_mapping = {}

        results = []
        for row in response_data:
            model = SamarClass(**row)
            if model.name in czak_mapping:
                model.example_models = czak_mapping[model.name]
            results.append(model)

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/samar-service-costs", tags=["Control Center"])
async def get_samar_service_costs() -> List[SamarServiceCost]:
    try:
        response = (
            supabase.table("samar_service_costs")
            .select("*")
            .order("samar_class_id")
            .order("engine_type_id")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [SamarServiceCost(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/samar-service-costs", tags=["Control Center"])
async def update_samar_service_cost(cost: SamarServiceCost) -> SamarServiceCost:
    try:
        data = cost.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("samar_service_costs").upsert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update service cost")
        response_data = cast(Any, response.data[0])
        return SamarServiceCost(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/samar-service-costs/{cost_id}", tags=["Control Center"])
async def delete_samar_service_cost(cost_id: str) -> Dict[str, str]:
    try:
        supabase.table("samar_service_costs").delete().eq("id", cost_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/samar-service-costs/export", tags=["Control Center"])
async def export_samar_service_costs() -> StreamingResponse:
    try:
        # Fetch all necessary data
        costs_resp = (
            supabase.table("samar_service_costs")
            .select(
                "id, samar_class_id, engine_type_id, power_band, cost_aso_per_km, cost_non_aso_per_km"
            )
            .execute()
        )
        classes_resp = supabase.table("samar_classes").select("id, name").execute()
        engines_resp = supabase.table("engines").select("id, name, category").execute()

        costs = costs_resp.data
        classes = {c["id"]: c["name"] for c in classes_resp.data}
        engines = {e["id"]: f"{e['name']} ({e['category']})" for e in engines_resp.data}

        # Build records for DataFrame
        records = []
        for row in costs:
            records.append(
                {
                    "ID": row["id"],  # Keep ID for import matching
                    "Klasa SAMAR": classes.get(row["samar_class_id"], "Unknown"),
                    "Napęd (Silnik)": engines.get(row["engine_type_id"], "Unknown"),
                    "Przedział Mocy": row["power_band"],
                    "Koszt ASO za km (Netto)": row["cost_aso_per_km"],
                    "Koszt Non-ASO za km (Netto)": row["cost_non_aso_per_km"],
                }
            )

        df = pd.DataFrame(records)

        # Save to memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Koszty Serwisowe")

            # Optional: adjust column widths for readability
            worksheet = writer.sheets["Koszty Serwisowe"]
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except Exception:
                        pass
                adjusted_width = max_length + 2
                worksheet.column_dimensions[column].width = adjusted_width

        output.seek(0)

        headers = {
            "Content-Disposition": "attachment; filename=koszty_serwisowe_eksport.xlsx"
        }
        return StreamingResponse(
            output,
            headers=headers,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/samar-service-costs/import", tags=["Control Center"])
async def import_samar_service_costs(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Validate columns
        required_cols = ["ID", "Koszt ASO za km (Netto)", "Koszt Non-ASO za km (Netto)"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Brakujące kolumny w pliku Excel: {', '.join(missing)}",
            )

        # Process updates
        updated_count = 0
        updates_batch = []
        for index, row in df.iterrows():
            row_id = str(row["ID"])
            if pd.isna(row_id) or row_id.strip() == "":
                continue

            cost_aso = float(row["Koszt ASO za km (Netto)"])
            cost_non_aso = float(row["Koszt Non-ASO za km (Netto)"])

            # Simple batch logic: keep track and upsert one by one via supabase
            # (Bulk isn't simple with Supabase Python without upsert array, so we use a loop or arrays)
            updates_batch.append(
                {
                    "id": row_id,
                    "cost_aso_per_km": cost_aso,
                    "cost_non_aso_per_km": cost_non_aso,
                }
            )

            # Update to database in smaller chunks or single upsert list
            # To be safe with supabase constraints, we can upsert only the required fields.
            # But supabase postgREST upsert requires the whole row or it merges. We will do a direct update.
            # Because upsert needs all non-null columns if they don't have defaults.
            supabase.table("samar_service_costs").update(
                {"cost_aso_per_km": cost_aso, "cost_non_aso_per_km": cost_non_aso}
            ).eq("id", row_id).execute()

            updated_count += 1

        return {
            "status": "success",
            "message": f"Pomyślnie zaktualizowano {updated_count} rekordów.",
            "updated_count": updated_count,
        }

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


# ── Brand Corrections CRUD ──


@app.get("/api/brand-corrections", tags=["Control Center"])
async def get_brand_corrections_crud() -> List[BrandCorrection]:
    try:
        response = (
            supabase.table("samar_brand_corrections")
            .select("*")
            .order("klasa_samar")
            .order("marka")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [BrandCorrection(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/brand-corrections", tags=["Control Center"])
async def upsert_brand_correction(item: BrandCorrection) -> BrandCorrection:
    try:
        data = item.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("samar_brand_corrections").upsert(data).execute()
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Nie udało się zapisać korekty marki"
            )
        response_data = cast(Any, response.data[0])
        return BrandCorrection(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/brand-corrections/{item_id}", tags=["Control Center"])
async def delete_brand_correction(item_id: str) -> Dict[str, str]:
    try:
        supabase.table("samar_brand_corrections").delete().eq("id", item_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Body Types Dictionary CRUD ──


class BodyType(BaseModel):
    id: Optional[int] = None
    name: str
    vehicle_class: str  # "Osobowy" / "Dostawczy"
    description: Optional[str] = None


@app.get("/api/body-types", tags=["Control Center"])
async def get_body_types() -> List[BodyType]:
    try:
        response = (
            supabase.table("body_types")
            .select("*")
            .order("vehicle_class")
            .order("name")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [BodyType(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/body-types", tags=["Control Center"])
async def upsert_body_type(body_type: BodyType) -> BodyType:
    try:
        data = body_type.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("body_types").upsert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to upsert body type")
        response_data = cast(Any, response.data[0])
        return BodyType(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/body-types/{body_type_id}", tags=["Control Center"])
async def delete_body_type(body_type_id: int) -> Dict[str, str]:
    try:
        supabase.table("body_types").delete().eq("id", body_type_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/replacement-car-rates", tags=["Control Center"])
async def get_replacement_car_rates() -> List[ReplacementCarRate]:
    try:
        response = (
            supabase.table("replacement_car_rates")
            .select("*")
            .order("samar_class_id")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [ReplacementCarRate(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/replacement-car-rates", tags=["Control Center"])
async def upsert_replacement_car_rate(item: ReplacementCarRate) -> ReplacementCarRate:
    try:
        data = item.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("replacement_car_rates").upsert(data).execute()
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Nie udało się zapisać stawki zastępczego"
            )
        response_data = cast(Any, response.data[0])
        return ReplacementCarRate(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/replacement-car-rates/{item_id}", tags=["Control Center"])
async def delete_replacement_car_rate(item_id: str) -> Dict[str, str]:
    try:
        supabase.table("replacement_car_rates").delete().eq("id", item_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calculate-matrix")
async def calculate_matrix(data: CalculatorInput) -> Dict[str, Any]:
    try:
        from core.LTRKalkulator import LTRKalkulator

        response = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Control center settings not found"
            )
        response_data = cast(Any, response.data[0])
        settings = ControlCenterSettings(**response_data)

        # Allow frontend wibor and margin to take precedence if they are explicitly sent,
        # otherwise they use the Pydantic defaults from CalculatorInput or UI values.

        engine = LTRKalkulator(input_data=data, settings=settings)
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

    uvicorn.run(app, host="127.0.0.1", port=8000)
