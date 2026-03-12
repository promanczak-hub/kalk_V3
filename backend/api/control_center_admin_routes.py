from typing import Any, Dict, List, cast, Optional
import io
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from core.database import supabase
from core.models import ControlCenterSettings
from api.schemas.control_center import (
    TyreCost,
    ServiceRate,
    ServiceBaseCost,
    EngineType,
    SamarClass,
    SamarServiceCost,
    ReplacementCarRate,
    BrandCorrection,
    DepreciationRate,
    MileageCorrection,
    BodyType,
    BodyCorrection,
    ZabudowaType,
    ZabudowaCorrection,
    PaintType,
    VintageCorrection,
)

router = APIRouter(tags=["Control Center"])


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
        response = supabase.table("control_center").update(data).eq("id", 1).execute()

        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to update control center settings"
            )

        response_data = cast(Any, response.data[0])
        return ControlCenterSettings(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tyre-costs")
async def get_tyre_costs() -> List[TyreCost]:
    try:
        response = (
            supabase.table("tyre_costs").select("*").order("tyre_class").execute()
        )
        response_data = cast(Any, response.data)
        return [TyreCost(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tyre-costs")
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


@router.delete("/tyre-costs/{cost_id}")
async def delete_tyre_cost(cost_id: str) -> Dict[str, str]:
    try:
        supabase.table("tyre_costs").delete().eq("id", cost_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engines")
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


@router.post("/engines")
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


@router.delete("/engines/{engine_id}")
async def delete_engine(engine_id: int) -> Dict[str, str]:
    try:
        supabase.table("engines").delete().eq("id", engine_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Depreciation Rates (per engine × samar_class × year) ---


@router.get("/depreciation-rates")
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


@router.post("/depreciation-rates")
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


@router.post("/depreciation-rates/bulk")
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


@router.delete("/depreciation-rates/{rate_id}")
async def delete_depreciation_rate(rate_id: int) -> Dict[str, str]:
    try:
        supabase.table("samar_class_depreciation_rates").delete().eq(
            "id", rate_id
        ).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Mileage Corrections (per engine × samar_class) ---


@router.get("/mileage-corrections")
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


@router.post("/mileage-corrections/bulk")
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


@router.delete("/mileage-corrections/{correction_id}")
async def delete_mileage_correction(correction_id: int) -> Dict[str, str]:
    try:
        supabase.table("samar_class_mileage_corrections").delete().eq(
            "id", correction_id
        ).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/samar-classes")
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
        # czak_mapping uses old format (no "Klasa"), samar_classes uses new format
        # Build a normalized czak lookup for fuzzy name matching
        czak_norm_map: Dict[str, str] = {}
        for raw_name, models in czak_mapping.items():
            norm = raw_name.strip().upper().replace("KLASA ", "")
            czak_norm_map[norm] = models

        for row in response_data:
            model = SamarClass(**row)
            # Try exact match first, then normalized
            if model.name in czak_mapping:
                model.example_models = czak_mapping[model.name]
            else:
                norm_key = model.name.strip().upper().replace("KLASA ", "")
                if norm_key in czak_norm_map:
                    model.example_models = czak_norm_map[norm_key]
            results.append(model)

        return results
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


@router.get("/service-rates")
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


@router.post("/service-rates")
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


@router.delete("/service-rates/{rate_id}")
async def delete_service_rate(rate_id: int) -> Dict[str, str]:
    try:
        supabase.table("service_rates_config").delete().eq("id", rate_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/service-base-costs")
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


@router.post("/service-base-costs")
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


@router.delete("/service-base-costs/{cost_id}")
async def delete_service_base_cost(cost_id: int) -> Dict[str, str]:
    try:
        supabase.table("service_base_costs_config").delete().eq("id", cost_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Brand Corrections CRUD (ltr_admin_korekta_wr_markas) ──


@router.get("/brand-corrections")
async def get_brand_corrections_crud() -> list[dict[str, Any]]:
    try:
        response = (
            supabase.table("ltr_admin_korekta_wr_markas")
            .select("*")
            .order("samar_class_id")
            .order("brand_name")
            .execute()
        )
        return cast(list[dict[str, Any]], response.data or [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brand-corrections")
async def upsert_brand_correction(item: BrandCorrection) -> dict[str, Any]:
    try:
        data = item.model_dump(exclude_unset=True)
        data["brand_name"] = (data.get("brand_name") or "").strip().upper()
        if data.get("model_name"):
            data["model_name"] = data["model_name"].strip()
        if not data.get("id"):
            data.pop("id", None)
        response = (
            supabase.table("ltr_admin_korekta_wr_markas")
            .upsert(
                data,
                on_conflict="samar_class_id,rodzaj_paliwa,brand_name",
            )
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Nie udało się zapisać korekty marki"
            )
        return cast(dict[str, Any], response.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/brand-corrections/{item_id}")
async def delete_brand_correction(item_id: int) -> Dict[str, str]:
    try:
        supabase.table("ltr_admin_korekta_wr_markas").delete().eq(
            "id", item_id
        ).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Body Types Dictionary CRUD ──


@router.get("/body-types")
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


@router.post("/body-types")
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


@router.delete("/body-types/{body_type_id}")
async def delete_body_type(body_type_id: int) -> Dict[str, str]:
    try:
        supabase.table("body_types").delete().eq("id", body_type_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/replacement-car-rates")
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


@router.post("/replacement-car-rates")
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


@router.delete("/replacement-car-rates/{item_id}")
async def delete_replacement_car_rate(item_id: str) -> Dict[str, str]:
    try:
        supabase.table("replacement_car_rates").delete().eq("id", item_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Body Type WR Corrections CRUD (Sparse) ──


@router.get("/body-corrections")
async def get_body_corrections(
    samar_class_id: Optional[int] = None,
) -> List[BodyCorrection]:
    try:
        q = supabase.table("body_type_wr_corrections").select("*").order("id")
        if samar_class_id is not None:
            q = q.eq("samar_class_id", samar_class_id)
        response = q.execute()
        response_data = (
            cast(List[Dict[str, Any]], response.data) if response.data else []
        )
        return [BodyCorrection(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/body-corrections")
async def upsert_body_correction(item: BodyCorrection) -> BodyCorrection:
    try:
        data = item.model_dump(exclude_unset=True)
        data.pop("id", None)
        # Normalize brand_name
        if data.get("brand_name"):
            data["brand_name"] = str(data["brand_name"]).strip().upper()
        response = supabase.table("body_type_wr_corrections").upsert(data).execute()
        response_data = (
            cast(List[Dict[str, Any]], response.data) if response.data else []
        )
        if not response_data:
            raise HTTPException(
                status_code=500, detail="Failed to upsert body correction"
            )
        return BodyCorrection(**response_data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/body-corrections/{correction_id}")
async def delete_body_correction(correction_id: int) -> Dict[str, str]:
    try:
        supabase.table("body_type_wr_corrections").delete().eq(
            "id", correction_id
        ).execute()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Zabudowa Types Dictionary CRUD ──


@router.get("/zabudowa-types")
async def get_zabudowa_types() -> List[ZabudowaType]:
    try:
        response = supabase.table("zabudowa_types").select("*").order("id").execute()
        response_data = cast(Any, response.data)
        return [ZabudowaType(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zabudowa-types")
async def upsert_zabudowa_type(item: ZabudowaType) -> ZabudowaType:
    try:
        data = item.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("zabudowa_types").upsert(data).execute()
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Nie udało się zapisać typu zabudowy"
            )
        response_data = cast(Any, response.data[0])
        return ZabudowaType(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/zabudowa-types/{type_id}")
async def delete_zabudowa_type(type_id: int) -> Dict[str, str]:
    try:
        supabase.table("zabudowa_types").delete().eq("id", type_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zabudowa-corrections")
async def get_zabudowa_corrections(
    zabudowa_type_id: Optional[int] = None,
    samar_class_id: Optional[int] = None,
) -> List[ZabudowaCorrection]:
    try:
        q = supabase.table("zabudowa_wr_corrections").select("*").order("id")
        if zabudowa_type_id is not None:
            q = q.eq("zabudowa_type_id", zabudowa_type_id)
        if samar_class_id is not None:
            q = q.eq("samar_class_id", samar_class_id)
        response = q.execute()
        response_data = cast(Any, response.data) if response.data else []
        return [ZabudowaCorrection(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zabudowa-corrections")
async def upsert_zabudowa_correction(
    item: ZabudowaCorrection,
) -> ZabudowaCorrection:
    try:
        data = item.model_dump(exclude_unset=True)
        if not data.get("id"):
            data.pop("id", None)
        response = supabase.table("zabudowa_wr_corrections").upsert(data).execute()
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Nie udało się zapisać korekty zabudowy"
            )
        response_data = cast(Any, response.data[0])
        return ZabudowaCorrection(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/zabudowa-corrections/{correction_id}")
async def delete_zabudowa_correction(correction_id: int) -> Dict[str, str]:
    try:
        supabase.table("zabudowa_wr_corrections").delete().eq(
            "id", correction_id
        ).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Paint Types WR Correction CRUD ──


@router.get("/paint-types")
async def get_paint_types() -> List[PaintType]:
    try:
        response = (
            supabase.table("paint_types")
            .select("id, name, wr_correction")
            .order("id")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [PaintType(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paint-types/bulk")
async def bulk_update_paint_types(
    items: List[PaintType],
) -> Dict[str, Any]:
    try:
        updated = 0
        for item in items:
            if item.id is None:
                continue
            supabase.table("paint_types").update(
                {"wr_correction": item.wr_correction}
            ).eq("id", item.id).execute()
            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Vintage (Rocznik) Correction CRUD ──


@router.get("/vintage-corrections")
async def get_vintage_corrections() -> List[VintageCorrection]:
    try:
        response = (
            supabase.table("ltr_admin_korekta_wr_roczniks")
            .select("id, rocznik, korekta_procent")
            .order("id")
            .execute()
        )
        response_data = cast(Any, response.data)
        return [VintageCorrection(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vintage-corrections/bulk")
async def bulk_update_vintage_corrections(
    items: List[VintageCorrection],
) -> Dict[str, Any]:
    try:
        updated = 0
        for item in items:
            if item.id is None:
                continue
            supabase.table("ltr_admin_korekta_wr_roczniks").update(
                {"korekta_procent": item.korekta_procent}
            ).eq("id", item.id).execute()
            updated += 1
        return {"status": "success", "count": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
