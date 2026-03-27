from typing import Any, Dict, List, cast, Optional
import io
import logging
import pandas as pd
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from core.database import supabase
from core.models import ControlCenterSettings
from core.config_cache import config_cache
from api.schemas.control_center import (
    BrandCorrection,
    DepreciationRate,
    EngineType,
    MileageCorrection,
    PaintType,
    ReplacementCarRate,
    SamarClass,
    SamarClassBaseRV,
    SamarClassServiceRate,
    SamarServiceCost,
    ServiceMultiplier,
    VintageCorrection,
)

router = APIRouter(tags=["Control Center Admin"])
logger = logging.getLogger(__name__)

# --- Mapping Layer Constants (Online DB compatibility) ---
SERVICE_RATE_MAP = {
    "samar_class_id": "klasa_samar_fk",
    "mileage_up_to": "przebieg_do",
    "cost_aso_per_km": "stawka_aso_per_km",
    "cost_non_aso_per_km": "stawka_non_aso_per_km",
}

REPLACEMENT_CAR_MAP = {
    "samar_class_id": "klasa_samar_fk",
    "average_days_per_year": "srednia_l_dni_rok",
    "daily_rate_net": "stawka_dzienna_netto_zl",
}

FUEL_TO_COL = {
    1: "benzyna_pb",
    2: "diesel_on",
    3: "benzyna_mhev_pb_mhev",
    4: "diesel_mhev_on_mhev",
    5: "hybryda_hev",
    6: "plug_in_hybrid_phev",
    7: "elektryczny_bev",
    8: "wodor_fcev",
    9: "lpg",
}
COL_TO_FUEL = {v: k for k, v in FUEL_TO_COL.items()}


@router.get("/brand-corrections")
async def get_brand_corrections() -> List[BrandCorrection]:
    try:
        response = supabase.table("ltr_admin_korekta_wr_markas").select("*").execute()
        data = []
        rows = cast(List[Dict[str, Any]], response.data or [])
        for row in rows:
            data.append(
                BrandCorrection(
                    id=row["id"],
                    brand_name=row["marka"],
                    correction_percent=row["korekta_procent"] or 0.0,
                    samar_class_id=0,
                    rodzaj_paliwa=1,
                )
            )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brand-corrections/bulk")
async def bulk_upsert_brand_corrections(
    items: List[BrandCorrection],
) -> Dict[str, Any]:
    try:
        updated = 0
        for item in items:
            d = {
                "marka": item.brand_name,
                "korekta_procent": item.correction_percent,
            }
            if item.id:
                supabase.table("ltr_admin_korekta_wr_markas").upsert(
                    {**d, "id": item.id}
                ).execute()
            else:
                supabase.table("ltr_admin_korekta_wr_markas").insert(d).execute()
            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vintage-corrections")
async def get_vintage_corrections() -> List[VintageCorrection]:
    try:
        response = supabase.table("ltr_admin_korekta_wr_roczniks").select("*").execute()
        data = []
        rows = cast(List[Dict[str, Any]], response.data or [])
        for row in rows:
            data.append(
                VintageCorrection(
                    id=row["id"],
                    rocznik=str(row["rocznik"]),
                    korekta_procent=row["korekta_procent"] or 0.0,
                )
            )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vintage-corrections/bulk")
async def bulk_upsert_vintage_corrections(
    items: List[VintageCorrection],
) -> Dict[str, Any]:
    try:
        updated = 0
        for item in items:
            d = {
                "rocznik": item.year,
                "korekta_procent": item.correction_percent,
            }
            if item.id:
                supabase.table("ltr_admin_korekta_wr_roczniks").upsert(
                    {**d, "id": item.id}
                ).execute()
            else:
                supabase.table("ltr_admin_korekta_wr_roczniks").insert(d).execute()
            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paint-types")
async def get_paint_types() -> List[PaintType]:
    try:
        response = supabase.table("paint_types").select("*").execute()
        data = []
        rows = cast(List[Dict[str, Any]], response.data or [])
        for row in rows:
            data.append(
                PaintType(
                    id=row["id"],
                    name=row["name"],
                    wr_correction=row["wr_correction"] or 0.0,
                )
            )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paint-types/bulk")
async def bulk_upsert_paint_types(
    items: List[PaintType],
) -> Dict[str, Any]:
    try:
        updated = 0
        for item in items:
            d = {
                "name": item.name,
                "wr_correction": item.wr_correction,
            }
            if item.id:
                supabase.table("paint_types").upsert({**d, "id": item.id}).execute()
            else:
                supabase.table("paint_types").insert(d).execute()
            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/control-center")
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


@router.post("/control-center")
async def update_control_center(
    settings: ControlCenterSettings,
) -> ControlCenterSettings:
    try:
        data = settings.model_dump()
        data["id"] = 1
        data["last_settings_update"] = datetime.now(timezone.utc).isoformat()

        response = supabase.table("control_center").update(data).eq("id", 1).execute()

        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to update control center settings"
            )

        response_data = cast(Any, response.data[0])
        return ControlCenterSettings(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engines")
async def get_engines() -> List[EngineType]:
    cached = config_cache.get("engines")
    if cached is not None:
        return cached
    try:
        response = (
            supabase.table("engines")
            .select("*")
            .order("category")
            .order("name")
            .execute()
        )
        response_data = cast(Any, response.data)
        result = [EngineType(**row) for row in response_data]
        config_cache.set("engines", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engines")
async def update_engine(engine: EngineType) -> EngineType:
    try:
        data = engine.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("engines").upsert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update engine")
        config_cache.invalidate("engines")
        response_data = cast(Any, response.data[0])
        return EngineType(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/engines/{engine_id}")
async def delete_engine(engine_id: int) -> Dict[str, str]:
    try:
        supabase.table("engines").delete().eq("id", engine_id).execute()
        config_cache.invalidate("engines")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Depreciation Rates (per engine × samar_class × year) ---


@router.get("/depreciation-rates")
async def get_depreciation_rates(
    samar_class_id: Optional[int] = None,
) -> List[DepreciationRate]:
    try:
        # Base rates from Wide table
        res_base = (
            supabase.table("samar_class_depreciation_rates").select("*").execute()
        )
        # Options rates from Tall table
        res_opts = supabase.table("samar_class_options_rv").select("*").execute()

        tall_rates = []
        rows_base = cast(List[Dict[str, Any]], res_base.data or [])
        rows_opts = cast(List[Dict[str, Any]], res_opts.data or [])

        # Pivot Base rates (Wide -> Tall)
        for row in rows_base:
            s_class_id = row["klasa_samar"]
            for engine_id, col in FUEL_TO_COL.items():
                if col in row:
                    tall_rates.append(
                        DepreciationRate(
                            samar_class_id=s_class_id,
                            fuel_type_id=engine_id,
                            year=1,
                            base_depreciation_percent=row[col] or 0.0,
                            options_depreciation_percent=0.0,
                        )
                    )

        # Merge Options rates (Tall)
        for opt in rows_opts:
            match = next(
                (
                    r
                    for r in tall_rates
                    if r.samar_class_id == opt["samar_class_id"]
                    and r.fuel_type_id == opt["engine_type_id"]
                    and r.year == opt["year"]
                ),
                None,
            )
            if match:
                match.options_depreciation_percent = opt["options_rv_percent"]
                if not match.id:
                    match.id = opt["id"]
            else:
                tall_rates.append(
                    DepreciationRate(
                        id=opt["id"],
                        samar_class_id=opt["samar_class_id"],
                        fuel_type_id=opt["engine_type_id"],
                        year=opt["year"],
                        base_depreciation_percent=0.0,
                        options_depreciation_percent=opt["options_rv_percent"],
                    )
                )

        if samar_class_id:
            return [r for r in tall_rates if r.samar_class_id == samar_class_id]
        return tall_rates

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/depreciation-rates/bulk")
async def bulk_upsert_depreciation_rates(
    rates: List[DepreciationRate],
) -> Dict[str, Any]:
    try:
        updated = 0
        for rate in rates:
            # Update Base (Wide Table)
            col_name = FUEL_TO_COL.get(rate.fuel_type_id)
            if col_name:
                supabase.table("samar_class_depreciation_rates").upsert(
                    {
                        "klasa_samar": rate.samar_class_id,
                        col_name: rate.base_depreciation_percent,
                    },
                    on_conflict="klasa_samar",
                ).execute()

            # Update Options (Tall Table)
            opt_data = {
                "samar_class_id": rate.samar_class_id,
                "engine_type_id": rate.fuel_type_id,
                "year": rate.year,
                "options_rv_percent": rate.options_depreciation_percent,
            }
            supabase.table("samar_class_options_rv").upsert(
                opt_data, on_conflict="samar_class_id, engine_type_id, year"
            ).execute()

            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/depreciation-rates/{rate_id}")
async def delete_depreciation_rate(rate_id: int) -> Dict[str, str]:
    try:
        # Note: rate_id in Tall format usually refers to the options table
        supabase.table("samar_class_options_rv").delete().eq("id", rate_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Mileage Corrections (per engine × samar_class) ---


@router.get("/samar-classes")
async def get_samar_classes() -> List[SamarClass]:
    cached = config_cache.get("samar_classes")
    if cached is not None:
        return cached
    try:
        response = supabase.table("samar_classes").select("*").order("id").execute()
        response_data = cast(Any, response.data)

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
        czak_norm_map: Dict[str, str] = {}
        for raw_name, models in czak_mapping.items():
            norm = raw_name.strip().upper().replace("KLASA ", "")
            czak_norm_map[norm] = models

        for row in response_data:
            model = SamarClass(**row)
            if model.name in czak_mapping:
                model.example_models = czak_mapping[model.name]
            else:
                norm_key = model.name.strip().upper().replace("KLASA ", "")
                if norm_key in czak_norm_map:
                    model.example_models = czak_norm_map[norm_key]
            results.append(model)

        config_cache.set("samar_classes", results)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Base RV Matrix (per engine × samar_class)# ── Samar Class Base RV CRUD ──


@router.get("/samar-class-base-rv", response_model=List[SamarClassBaseRV])
async def get_all_samar_class_base_rv() -> List[SamarClassBaseRV]:
    try:
        response = (
            supabase.table("samar_class_base_rv")
            .select("id, samar_class_id, engine_type_id, base_rv_percent")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [SamarClassBaseRV(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/samar-class-base-rv/{samar_class_id}")
async def get_samar_class_base_rv(samar_class_id: int) -> List[SamarClassBaseRV]:
    try:
        response = (
            supabase.table("samar_class_base_rv")
            .select("id, samar_class_id, engine_type_id, base_rv_percent")
            .eq("samar_class_id", samar_class_id)
            .execute()
        )
        response_data = cast(Any, response.data)
        return [SamarClassBaseRV(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/samar-class-base-rv/bulk")
async def bulk_upsert_base_rv(payload: List[SamarClassBaseRV]) -> Dict[str, Any]:
    try:
        data_list = []
        for item in payload:
            d = item.model_dump(exclude_unset=True)
            if not d.get("id"):
                d.pop("id", None)
            data_list.append(d)

        response = (
            supabase.table("samar_class_base_rv")
            .upsert(data_list, on_conflict="samar_class_id, engine_type_id")
            .execute()
        )
        return {"status": "success", "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/samar-service-costs")
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


@router.post("/samar-service-costs")
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


@router.delete("/samar-service-costs/{cost_id}")
async def delete_samar_service_cost(cost_id: str) -> Dict[str, str]:
    try:
        supabase.table("samar_service_costs").delete().eq("id", cost_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/samar-service-costs/export")
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

        costs = cast(List[Dict[str, Any]], costs_resp.data or [])
        classes = {
            c["id"]: c["name"]
            for c in cast(List[Dict[str, Any]], classes_resp.data or [])
        }
        engines = {
            e["id"]: f"{e['name']} ({e['category']})"
            for e in cast(List[Dict[str, Any]], engines_resp.data or [])
        }

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


@router.post("/samar-service-costs/import")
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

            updates_batch.append(
                {
                    "id": row_id,
                    "cost_aso_per_km": cost_aso,
                    "cost_non_aso_per_km": cost_non_aso,
                }
            )

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


@router.post("/service-multipliers/{multi_type}")
async def upsert_service_multiplier(
    multi_type: str, item: ServiceMultiplier
) -> ServiceMultiplier:
    valid_types = {"brand", "fuel", "drive", "gearbox"}
    if multi_type not in valid_types:
        raise HTTPException(status_code=400, detail="Invaild multiplier type")

    table_name = f"samar_service_{multi_type}_multipliers"
    col_name = f"{multi_type}_normalized"

    try:
        data = {
            col_name: item.name_normalized.strip().upper(),
            "multiplier": item.multiplier,
        }
        if item.id:
            data["id"] = item.id

        response = (
            supabase.table(table_name).upsert(data, on_conflict=col_name).execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to upsert multiplier")

        row = cast(Dict[str, Any], response.data[0])
        return ServiceMultiplier(
            id=str(row.get("id")),
            name_normalized=str(row.get(col_name, "")),
            multiplier=float(row.get("multiplier", 1.0)),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/service-multipliers/{multi_type}/{item_id}")
async def delete_service_multiplier(multi_type: str, item_id: str) -> Dict[str, str]:
    valid_types = {"brand", "fuel", "drive", "gearbox"}
    if multi_type not in valid_types:
        raise HTTPException(status_code=400, detail="Invaild multiplier type")

    table_name = f"samar_service_{multi_type}_multipliers"
    try:
        supabase.table(table_name).delete().eq("id", item_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/replacement-car-rates")
async def get_replacement_car_rates() -> List[ReplacementCarRate]:
    try:
        response = (
            supabase.table("replacement_car_rates")
            .select("*")
            .order("klasa_samar_fk")
            .execute()
        )
        data = []
        rows = cast(List[Dict[str, Any]], response.data or [])
        for row in rows:
            data.append(
                ReplacementCarRate(
                    id=str(row["id"]),
                    samar_class_id=row["klasa_samar_fk"],
                    average_days_per_year=row["srednia_l_dni_rok"],
                    daily_rate_net=row["stawka_dzienna_netto_zl"],
                )
            )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replacement-car-rates/bulk")
async def bulk_upsert_replacement_car_rates(
    items: List[ReplacementCarRate],
) -> Dict[str, Any]:
    try:
        updated = 0
        for item in items:
            d = {
                "klasa_samar_fk": item.samar_class_id,
                "srednia_l_dni_rok": item.average_days_per_year,
                "stawka_dzienna_netto_zl": item.daily_rate_net,
            }
            if item.id:
                supabase.table("replacement_car_rates").upsert(
                    {**d, "id": item.id}
                ).execute()
            else:
                supabase.table("replacement_car_rates").insert(d).execute()
            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/replacement-car-rates/{item_id}")
async def delete_replacement_car_rate(item_id: str) -> Dict[str, str]:
    try:
        supabase.table("replacement_car_rates").delete().eq("id", item_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/samar-class-service-rates")
async def get_samar_class_service_rates() -> List[SamarClassServiceRate]:
    try:
        response = (
            supabase.table("samar_class_service_rates")
            .select("*")
            .order("klasa_samar_fk")
            .order("przebieg_do")
            .execute()
        )
        data = []
        rows = cast(List[Dict[str, Any]], response.data or [])
        for row in rows:
            data.append(
                SamarClassServiceRate(
                    id=str(row["id"]),
                    samar_class_id=row["klasa_samar_fk"],
                    mileage_up_to=row["przebieg_do"],
                    cost_aso_per_km=row["stawka_aso_per_km"],
                    cost_non_aso_per_km=row["stawka_non_aso_per_km"],
                )
            )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/samar-class-service-rates/bulk")
async def bulk_upsert_samar_class_service_rates(
    rates: List[SamarClassServiceRate],
) -> Dict[str, Any]:
    try:
        updated = 0
        for item in rates:
            d = {
                "klasa_samar_fk": item.samar_class_id,
                "przebieg_do": item.mileage_up_to,
                "stawka_aso_per_km": item.cost_aso_per_km,
                "stawka_non_aso_per_km": item.cost_non_aso_per_km,
            }
            if item.id:
                supabase.table("samar_class_service_rates").upsert(
                    {**d, "id": item.id}
                ).execute()
            else:
                supabase.table("samar_class_service_rates").insert(d).execute()
            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/samar-class-service-rates/{rate_id}")
async def delete_samar_class_service_rate(rate_id: str) -> Dict[str, str]:
    try:
        supabase.table("samar_class_service_rates").delete().eq("id", rate_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mileage-corrections")
async def get_mileage_corrections() -> List[MileageCorrection]:
    try:
        response = (
            supabase.table("samar_class_mileage_corrections")
            .select("*")
            .order("klasa_samar")
            .execute()
        )
        data = []
        rows = cast(List[Dict[str, Any]], response.data or [])
        for row in rows:
            data.append(
                MileageCorrection(
                    id=row["id"],
                    samar_class_id=row["klasa_samar"],
                    fuel_type_id=1,  # Global default for online schema
                    under_threshold_percent=row["korekta_lt_prog"],
                    over_threshold_percent=row["korekta_gt_prog"],
                )
            )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mileage-corrections/bulk")
async def bulk_upsert_mileage_corrections(
    items: List[MileageCorrection],
) -> Dict[str, Any]:
    try:
        updated = 0
        for item in items:
            d = {
                "klasa_samar": item.samar_class_id,
                "korekta_lt_prog": item.under_threshold_percent,
                "korekta_gt_prog": item.over_threshold_percent,
            }
            if item.id:
                supabase.table("samar_class_mileage_corrections").upsert(
                    {**d, "id": item.id}
                ).execute()
            else:
                supabase.table("samar_class_mileage_corrections").insert(d).execute()
            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
