from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, Optional, List, cast
from datetime import datetime
import uuid
import logging
from core.database import supabase
from api.schemas.pricing import PricingPatch, PricingResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kalkulacje", tags=["kalkulacje"])


class CreateKalkulacjaRequest(BaseModel):
    stan_json: dict
    source: Literal["pdf", "manual", "clone"] = "pdf"


class CreateManualRequest(BaseModel):
    """Payload do tworzenia kalkulacji manualnej bez ekstrakcji PDF."""

    brand: str
    model: str
    version: str = ""
    fuel_type: str = ""
    body_type: str = ""
    engine_name: str = ""
    samar_category: str = ""
    rok: Optional[int] = None
    # Parametry LTR
    okres_bazowy: int = Field(default=48)
    przebieg_bazowy: int = Field(default=140000)
    # Sekcja cenowa (deterministyczna)
    pricing: Optional[PricingPatch] = None


class AskAiRequest(BaseModel):
    step_name: str
    inputs: dict
    outputs: dict
    metadata: Optional[dict] = None
    query: str


class StatusUpdateRequest(BaseModel):
    status: str


VALID_STATUSES = [
    "szkic_vertex",
    "w_opracowaniu",
    "gotowa",
    "wyslana",
    "archiwum",
]


class KalkulacjaResponse(BaseModel):
    id: str
    numer_kalkulacji: str
    status: str
    source: Optional[str] = "pdf"
    dane_pojazdu: Optional[str]
    cena_netto: Optional[float]
    created_at: str
    updated_at: str
    stan_json: Optional[dict] = None


class KalkulacjaListItem(BaseModel):
    id: str
    numer_kalkulacji: str
    status: str
    source: Optional[str] = "pdf"
    dane_pojazdu: Optional[str] = None
    cena_netto: Optional[float] = None
    created_at: str
    updated_at: str
    body_type: Optional[str] = None
    fuel_type: Optional[str] = None
    discount_pct: Optional[float] = None
    options_count: int = 0


@router.post("", response_model=KalkulacjaResponse)
def create_kalkulacja(req: CreateKalkulacjaRequest):
    brand = req.stan_json.get("brand", "")
    model = req.stan_json.get("model", "")
    dane_pojazdu = f"{brand} {model}".strip() if brand or model else "Nieznany Pojazd"

    cena_netto = req.stan_json.get("base_price_net", 0.0)

    now = datetime.now()
    short_uuid = uuid.uuid4().hex[:6].upper()
    numer_kalkulacji = f"KALK/{now.year}/{now.month:02d}/{short_uuid}"

    stan = {**req.stan_json, "source": req.source}
    data = {
        "numer_kalkulacji": numer_kalkulacji,
        "status": "szkic_vertex",
        "stan_json": stan,
        "dane_pojazdu": dane_pojazdu,
        "cena_netto": cena_netto,
    }

    try:
        res = supabase.table("ltr_kalkulacje").insert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Błąd przy zapisie do bazy.")
        row = res.data[0]
        row["source"] = req.source
        
        trace_id = uuid.uuid4().hex
        logger.info("Triggering matrix calculation for new PDF kalkulacja %s [Trace: %s]", row["id"], trace_id)
        from tasks.matrix_tasks import process_kalkulacja_matrix_task
        process_kalkulacja_matrix_task.apply_async(args=[row["id"], trace_id])
        
        return row
    except Exception as e:
        logger.exception("POST /kalkulacje failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual", response_model=KalkulacjaResponse)
def create_manual_kalkulacja(req: CreateManualRequest):
    """Tworzy kalkulację manualną bez ekstrakcji PDF."""
    now = datetime.now()
    short_uuid = uuid.uuid4().hex[:6].upper()
    numer_kalkulacji = f"KALK/{now.year}/{now.month:02d}/{short_uuid}"
    dane_pojazdu = f"{req.brand} {req.model}".strip() or "Manualna Kalkulacja"

    pricing_dict = req.pricing.model_dump() if req.pricing else None
    cena_netto = _compute_purchase_price_net(req.pricing) if req.pricing else 0.0

    stan_json: Dict[str, Any] = {
        "source": "manual",
        "brand": req.brand,
        "model": req.model,
        "version": req.version,
        "fuel_type": req.fuel_type,
        "body_type": req.body_type,
        "engine_name": req.engine_name,
        "samar_category": req.samar_category,
        "rok": req.rok,
        "okres_bazowy": req.okres_bazowy,
        "przebieg_bazowy": req.przebieg_bazowy,
        "pricing": pricing_dict,
        "base_price_net": cena_netto,
    }

    try:
        res = (
            supabase.table("ltr_kalkulacje")
            .insert(
                {
                    "numer_kalkulacji": numer_kalkulacji,
                    "status": "szkic_vertex",
                    "stan_json": stan_json,
                    "dane_pojazdu": dane_pojazdu,
                    "cena_netto": cena_netto,
                }
            )
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=500, detail="Błąd przy zapisie manualnej kalkulacji."
            )
        row = res.data[0]
        row["source"] = "manual"
        
        trace_id = uuid.uuid4().hex
        logger.info("Triggering matrix calculation for manual kalkulacja %s [Trace: %s]", row["id"], trace_id)
        from tasks.matrix_tasks import process_kalkulacja_matrix_task
        process_kalkulacja_matrix_task.apply_async(args=[row["id"], trace_id])
        
        return row
    except Exception as e:
        logger.exception("POST /kalkulacje/manual failed")
        raise HTTPException(status_code=500, detail=str(e))


def _extract_list_fields(row: Dict[str, Any]) -> KalkulacjaListItem:
    """Extract enriched fields from stan_json for list view."""
    sj = cast(Dict[str, Any], row.get("stan_json") or {})
    vehicle_mapped = cast(Dict[str, Any], sj.get("vehicle_mapped") or {})
    discount_block = cast(Dict[str, Any], sj.get("discount") or {})

    factory_opts = sj.get("factory_options") or []
    service_opts = sj.get("service_options") or []
    source = sj.get("source", "pdf")

    return KalkulacjaListItem(
        id=row["id"],
        numer_kalkulacji=row["numer_kalkulacji"],
        status=row.get("status", "szkic_vertex"),
        source=source,
        dane_pojazdu=row.get("dane_pojazdu"),
        cena_netto=row.get("cena_netto"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        body_type=vehicle_mapped.get("body_type") or sj.get("body_type"),
        fuel_type=vehicle_mapped.get("fuel_type") or sj.get("fuel_type"),
        discount_pct=discount_block.get("active_discount_pct"),
        options_count=len(factory_opts) + len(service_opts),
    )


def _compute_purchase_price_net(pricing: PricingPatch) -> float:
    """Deterministyczne obliczenie ceny zakupu netto z panelu cenowego."""
    discountable = sum(c.amount_net for c in pricing.components if not c.no_discount)
    non_discountable = sum(c.amount_net for c in pricing.components if c.no_discount)
    after_discount = discountable * (1 - pricing.discount_pct / 100)
    return round(after_discount + non_discountable, 2)


def _compute_pricing_result(pricing: PricingPatch) -> PricingResult:
    """Pełny deterministyczny wynik panelu cenowego."""
    discountable = sum(c.amount_net for c in pricing.components if not c.no_discount)
    non_discountable = sum(c.amount_net for c in pricing.components if c.no_discount)
    total_sum = discountable + non_discountable
    discount_amount = round(discountable * pricing.discount_pct / 100, 2)
    purchase_price_net = round(discountable - discount_amount + non_discountable, 2)
    vat_amount = round(purchase_price_net * 0.23, 2)
    return PricingResult(
        components=pricing.components,
        discount_pct=pricing.discount_pct,
        discountable_sum=round(discountable, 2),
        non_discountable_sum=round(non_discountable, 2),
        total_sum_net=round(total_sum, 2),
        discount_amount=discount_amount,
        purchase_price_net=purchase_price_net,
        vat_amount=vat_amount,
        purchase_price_gross=round(purchase_price_net + vat_amount, 2),
    )


@router.get("", response_model=List[KalkulacjaListItem])
def get_kalkulacje():
    try:
        res = (
            supabase.table("ltr_kalkulacje")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return [_extract_list_fields(r) for r in res.data]
    except Exception as e:
        logger.exception("GET /kalkulacje failed")
        raise HTTPException(status_code=500, detail=str(e))


class MatrixCacheRefreshRequest(BaseModel):
    vehicle_ids: List[str]


@router.post("/matrix-cache/refresh")
async def refresh_matrix_cache(request: MatrixCacheRefreshRequest):
    """
    Ręczne wywołanie odświeżenia cache macierzy dla pojazdów.
    Zleca zadania do kolejki Celery, by nie blokować interfejsu ani pętli zdarzeń uvicorn.
    """
    try:
        if not request.vehicle_ids:
            return {"status": "error", "message": "Brak ID pojazdów."}
        
        from tasks.matrix_tasks import refresh_matrix_cache_for_vehicles_task
        
        # Split into chunks of 5 to avoid long-running celery tasks
        chunk_size = 5
        dispatched_tasks = 0
        for i in range(0, len(request.vehicle_ids), chunk_size):
            batch = request.vehicle_ids[i:i+chunk_size]
            refresh_matrix_cache_for_vehicles_task.apply_async(args=[batch])
            dispatched_tasks += 1
            
        return {
            "status": "success", 
            "message": f"Wysłano {len(request.vehicle_ids)} pojazd(ów) w {dispatched_tasks} transzach do Celery."
        }
    except Exception as e:
        logger.exception("Błąd w trakcie odświeżania cache macierzy.")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vehicle/{vehicle_id}", response_model=List[KalkulacjaListItem])
def get_kalkulacje_by_vehicle(vehicle_id: str):
    """Fetch calculations strictly associated with a given vehicle ID from vertex."""
    try:
        # We query the JSONB field stan_json->>'vehicle_id'
        res = (
            supabase.table("ltr_kalkulacje")
            .select("*")
            .eq("stan_json->>vehicle_id", vehicle_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [_extract_list_fields(r) for r in res.data]
    except Exception as e:
        logger.exception("GET /kalkulacje/vehicle/%s failed", vehicle_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kalk_id}", response_model=KalkulacjaResponse)
def get_kalkulacja(kalk_id: str):
    try:
        res = supabase.table("ltr_kalkulacje").select("*").eq("id", kalk_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Kalkulacja nie znaleziona")
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{kalk_id}")
def delete_kalkulacja(kalk_id: str):
    """Hard-delete a kalkulacja by ID."""
    try:
        res = supabase.table("ltr_kalkulacje").delete().eq("id", kalk_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Kalkulacja nie znaleziona")
        return {"status": "deleted", "id": kalk_id}
    except Exception as e:
        logger.exception("DELETE /kalkulacje/%s failed", kalk_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{kalk_id}/duplicate", response_model=KalkulacjaResponse)
def duplicate_kalkulacja(kalk_id: str):
    """Clone an existing kalkulacja with a new ID and numer."""
    try:
        res = supabase.table("ltr_kalkulacje").select("*").eq("id", kalk_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Kalkulacja nie znaleziona")

        original = res.data[0]
        now = datetime.now()
        short_uuid = uuid.uuid4().hex[:6].upper()
        new_numer = f"KALK/{now.year}/{now.month:02d}/{short_uuid}"

        orig_stan = dict(original.get("stan_json") or {})
        orig_stan["source"] = "clone"
        orig_name = original.get("dane_pojazdu", "Kalkulacja")
        new_data = {
            "numer_kalkulacji": new_numer,
            "status": "szkic_vertex",
            "stan_json": orig_stan,
            "dane_pojazdu": f"KOPIA: {orig_name}",
            "cena_netto": original.get("cena_netto", 0.0),
        }

        insert_res = supabase.table("ltr_kalkulacje").insert(new_data).execute()
        if not insert_res.data:
            raise HTTPException(status_code=500, detail="Błąd duplikacji")
        
        new_row = insert_res.data[0]
        
        trace_id = uuid.uuid4().hex
        logger.info("Triggering matrix calculation for duplicated kalkulacja %s [Trace: %s]", new_row["id"], trace_id)
        from tasks.matrix_tasks import process_kalkulacja_matrix_task
        process_kalkulacja_matrix_task.apply_async(args=[new_row["id"], trace_id])
        
        return new_row
    except Exception as e:
        logger.exception("DUPLICATE /kalkulacje/%s failed", kalk_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{kalk_id}/status")
def update_kalkulacja_status(kalk_id: str, req: StatusUpdateRequest):
    """Update status of a kalkulacja (workflow transition)."""
    if req.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"NieprawidĹ‚owy status '{req.status}'. "
            f"Dozwolone: {', '.join(VALID_STATUSES)}",
        )
    try:
        res = (
            supabase.table("ltr_kalkulacje")
            .update({"status": req.status})
            .eq("id", kalk_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Kalkulacja nie znaleziona")
        return {"status": "updated", "id": kalk_id, "new_status": req.status}
    except Exception as e:
        logger.exception("PATCH status /kalkulacje/%s failed", kalk_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{kalk_id}/pricing", response_model=PricingResult)
def patch_kalkulacja_pricing(kalk_id: str, patch: PricingPatch):
    """Aktualizuje sekcję cenową kalkulacji i zwraca obliczony wynik."""
    try:
        res = (
            supabase.table("ltr_kalkulacje")
            .select("stan_json")
            .eq("id", kalk_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Kalkulacja nie znaleziona")

        stan = dict(res.data[0].get("stan_json") or {})
        result = _compute_pricing_result(patch)
        stan["pricing"] = patch.model_dump()
        stan["base_price_net"] = result.purchase_price_net

        upd = (
            supabase.table("ltr_kalkulacje")
            .update({"stan_json": stan, "cena_netto": result.purchase_price_net})
            .eq("id", kalk_id)
            .execute()
        )
        if not upd.data:
            raise HTTPException(status_code=500, detail="Błąd aktualizacji cen")
            
        trace_id = uuid.uuid4().hex
        logger.info("Triggering recalculation for pricing patch %s [Trace: %s]", kalk_id, trace_id)
        from tasks.matrix_tasks import process_kalkulacja_matrix_task
        process_kalkulacja_matrix_task.apply_async(args=[kalk_id, trace_id])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PATCH /kalkulacje/%s/pricing failed", kalk_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{kalk_id}/recalculate")
def recalculate_kalkulacja(kalk_id: str):
    """Wyzwala przeliczenie matrycy LTR na podstawie bieżącego stan_json."""
    try:
        res = (
            supabase.table("ltr_kalkulacje")
            .select("stan_json", "id")
            .eq("id", kalk_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Kalkulacja nie znaleziona")

        trace_id = uuid.uuid4().hex
        logger.info("Triggering explicit recalculation for %s [Trace: %s]", kalk_id, trace_id)
        from tasks.matrix_tasks import process_kalkulacja_matrix_task
        process_kalkulacja_matrix_task.apply_async(args=[kalk_id, trace_id])
        
        return {"status": "queued", "kalk_id": kalk_id, "trace_id": trace_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /kalkulacje/%s/recalculate failed", kalk_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{kalk_id}/smart-advisor")
def get_smart_variants(kalk_id: str):
    """Generates 3 smart variants (Base, Best Value, Low Monthly) for a given calculation."""
    from api.schemas.calculator import CalculatorInput
    from core.models import ControlCenterSettings
    from core.LTRKalkulator import LTRKalkulator

    try:
        res = (
            supabase.table("ltr_kalkulacje")
            .select("stan_json", "numer_kalkulacji")
            .eq("id", kalk_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Kalkulacja nie znaleziona")

        row = res.data[0]
        stan = row.get("stan_json") or {}
        numer_kalkulacji = row.get("numer_kalkulacji", kalk_id)

        try:
            calc_input = CalculatorInput(**stan)
        except Exception as e:
            logger.warning(f"Failed to parse stan_json directly: {e}")
            raise HTTPException(
                status_code=400,
                detail="Nie mozna odtworzyc danych wejsciowych z kalkulacji.",
            )

        cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        cc_settings = ControlCenterSettings(**cc_res.data[0])

        engine = LTRKalkulator(input_data=calc_input, settings=cc_settings)
        matrix_cells = engine.build_matrix()

        base_months = calc_input.okres_bazowy or 48
        base_mileage = calc_input.przebieg_bazowy or 80000

        base_variant = None
        low_monthly = None
        best_value = None

        lowest_inst = float("inf")

        for cell in matrix_cells:
            m = cell.get("Okres", 0)
            km = cell.get("PrzebiegKontrakt", 0)
            inst = float(cell.get("RataNetto", 0))

            if m == base_months and km == base_mileage:
                base_variant = cell

            if 0 < inst < lowest_inst:
                lowest_inst = inst
                low_monthly = cell

            if m == 48 and km == 80000:
                best_value = cell

        if not base_variant and matrix_cells:
            base_variant = matrix_cells[0]
        if not best_value and matrix_cells:
            best_value = matrix_cells[len(matrix_cells) // 2]

        car_info = {
            "brand": stan.get("brand", ""),
            "model": stan.get("model", ""),
            "powertrain": stan.get("engine_name", ""),
            "vin_or_config": numer_kalkulacji,
        }

        def _map_to_offer(cell, reco):
            if not cell:
                return None
            return {
                "id": f"{kalk_id}_{cell.get('Okres')}_{cell.get('PrzebiegKontrakt')}",
                "brand": car_info["brand"],
                "model": car_info["model"],
                "powertrain": car_info["powertrain"],
                "vin_or_config": car_info["vin_or_config"],
                "term": cell.get("Okres"),
                "mileage": cell.get("PrzebiegKontrakt"),
                "net_installment": cell.get("RataNetto"),
                "contribution": calc_input.initial_deposit_pct,
                "system_recommendation": reco,
                "calculation_data": cell,
                "standard_equipment": [],
                "factory_options": [o.name for o in calc_input.factory_options]
                if calc_input.factory_options
                else [],
                "dealer_options": [o.name for o in calc_input.service_options]
                if calc_input.service_options
                else [],
            }

        variants = []
        if base_variant:
            variants.append(_map_to_offer(base_variant, "Twój Wybór"))
        if low_monthly and low_monthly != base_variant:
            variants.append(_map_to_offer(low_monthly, "Najniższa Rata"))
        if best_value and best_value not in [base_variant, low_monthly]:
            variants.append(_map_to_offer(best_value, "Optymalny Okres/Przebieg"))

        return {"status": "success", "variants": variants}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /kalkulacje/%s/smart-advisor failed", kalk_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug-pipeline/{vehicle_id}")
def debug_calculation_pipeline(vehicle_id: str, req: dict):
    from api.schemas.calculator import CalculatorInput, VehicleOptions
    from core.PipelineDebugger import PipelineDebugger
    from core.models import ControlCenterSettings
    from typing import cast, Any, Dict

    try:
        # Reconstruct Control Center Settings
        cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not cc_res.data:
            raise HTTPException(status_code=500, detail="Brak ustawieĹ„ CC")

        response_data = cast(Dict[str, Any], cc_res.data[0])
        settings = ControlCenterSettings(**response_data)

        # 1. Map options
        factory_opts = []
        for o in req.get("factory_options", []):
            factory_opts.append(
                VehicleOptions(
                    name=o["name"],
                    price_net=o["price_net"],
                    price_gross=round(o["price_net"] * 1.23, 2),
                )
            )
        service_opts = []
        for o in req.get("service_options", []):
            service_opts.append(
                VehicleOptions(
                    name=o["name"],
                    price_net=o["price_net"],
                    price_gross=round(o["price_net"] * 1.23, 2),
                    include_in_wr=o.get("include_in_wr", False),
                )
            )

        # 2. Map Payload into CalculatorInput
        calc_input = CalculatorInput(
            vehicle_id=vehicle_id,
            base_price_net=req.get("base_price_net", 0.0),
            discount_pct=req.get("discount_pct", 0.0),
            factory_options=factory_opts,
            service_options=service_opts,
            wibor_pct=req.get("wibor_pct", 5.85),
            margin_pct=req.get("margin_pct", 2.0),
            pricing_margin_pct=req.get("pricing_margin_pct", 15.0),
            depreciation_pct=req.get("depreciation_pct"),
            initial_deposit_pct=req.get("initial_deposit_pct", 0.0),
            z_oponami=req.get("z_oponami", True),
            klasa_opony_string=req.get("klasa_opony_string", "Medium"),
            srednica_felgi=req.get("srednica_felgi", 18),
            korekta_kosztu_opon=req.get("korekta_kosztu_opon", False),
            koszt_opon_korekta=req.get("koszt_opon_korekta", 0.0),
            service_cost_type=req.get("service_cost_type", "ASO"),
            okres_bazowy=req.get("okres_bazowy", 48),
            przebieg_bazowy=req.get("przebieg_bazowy", 140000),
            replacement_car_enabled=req.get("replacement_car_enabled", True),
            pakiet_serwisowy=req.get("pakiet_serwisowy", 0.0),
            inne_koszty_serwisowania_netto=req.get(
                "inne_koszty_serwisowania_netto", 0.0
            ),
            # Flagi kosztĂłw dodatkowych (globalne kwoty z CC, tu ON/OFF per kalkulacja)
            add_gsm_subscription=req.get("add_gsm_subscription", True),
            add_hook_installation=req.get("add_hook_installation", False),
            add_grid_dismantling=req.get("add_grid_dismantling", False),
            add_registration=req.get("add_registration", True),
            add_sales_prep=req.get("add_sales_prep", True),
            korekta_kosztu_przygotowania=req.get("korekta_kosztu_przygotowania", 0.0),
            odkup_opon_enabled=req.get("odkup_opon_enabled", False),
        )

        # 3. Handle overrides and months for execution
        months = req.get("months", calc_input.okres_bazowy)
        overrides = req.get("overrides", {})

        # 4. Call Debugger Engine
        debugger = PipelineDebugger(input_data=calc_input, settings=settings)
        steps = debugger.calculate_steps(months=months, overrides=overrides)
        report_html = debugger.render_steps_html(
            steps=steps,
            months=months,
            vehicle_id=vehicle_id,
        )

        return {
            "status": "success",
            "vehicle_id": vehicle_id,
            "months": months,
            "steps": steps,
            "report_html": report_html,
        }
    except Exception as e:
        print(f"Debugger Engine Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug-pipeline/{vehicle_id}/ask-ai")
def ask_ai_about_step(vehicle_id: str, req: AskAiRequest):
    from core.gemini_client import get_gemini_client
    from google.genai import types as genai_types
    import json

    try:
        client = get_gemini_client()

        prompt = f"""
JesteĹ› inĹĽynierem-asystentem w systemie kalkulatora leasingowego. UĹĽytkownik przeglÄ…da krok "{req.step_name}" w dziale Pipeline Debugger i zadaĹ‚ pytanie.
Oto kontekst tego kroku:
WEJĹšCIA (Inputs):
{json.dumps(req.inputs, indent=2, ensure_ascii=False)}

WYJĹšCIA (Outputs):
{json.dumps(req.outputs, indent=2, ensure_ascii=False)}

METADANE (Wzory i ĹąrĂłdĹ‚a):
{json.dumps(req.metadata or {}, indent=2, ensure_ascii=False)}

Pytanie uĹĽytkownika:
{req.query}

Odpowiedz krĂłtko i merytorycznie w jÄ™zyku polskim. WyjaĹ›nij dlaczego dany krok wyliczyĹ‚ takÄ… wartoĹ›Ä‡ (np. zero, lub danÄ… stawkÄ™). Wskazuj na konkretne WejĹ›cia (Inputs) lub Metadane (np. brak ustawieĹ„ w bazie).
BÄ…dĹş techniczny, przyjazny i konkretnie diagnozuj wynik. UĹĽywaj formatowania Markdown by wypunktowaÄ‡ kluczowe powody.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.0,
            ),
        )

        return {"status": "success", "answer": response.text}
    except Exception as e:
        print(f"AI Debugger Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── Calculation Jobs Status ──────────────────────────────────────────────────


class JobStatus(BaseModel):
    vehicle_id: str
    status: str
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    monthly_price_net: Optional[float] = None


class JobsStatusResponse(BaseModel):
    total: int
    done: int
    failed: int
    running: int
    queued: int
    failed_jobs: List[JobStatus]


@router.get("/jobs-status", response_model=JobsStatusResponse)
def get_jobs_status() -> JobsStatusResponse:
    """Status wszystkich jobów kalkulacyjnych Celery.

    Każdy failed job zawiera error_code wskazujący przyczynę
    (NO_BASE_PRICE, CALC_ERROR, NO_SAMAR_CLASS, itp.) bez fallbacków.
    """
    try:
        res = (
            supabase.table("calculation_jobs")
            .select("*")
            .order("queued_at", desc=True)
            .limit(500)
            .execute()
        )
        rows = res.data or []

        stats: dict[str, int] = {"done": 0, "failed": 0, "running": 0, "queued": 0}
        failed_jobs: list[JobStatus] = []

        for row in rows:
            s = str(row.get("status", "queued"))
            if s in stats:
                stats[s] += 1
            if s == "failed":
                failed_jobs.append(JobStatus(**row))

        return JobsStatusResponse(
            total=len(rows),
            done=stats["done"],
            failed=stats["failed"],
            running=stats["running"],
            queued=stats["queued"],
            failed_jobs=failed_jobs,
        )
    except Exception as e:
        logger.exception("GET /kalkulacje/jobs-status failed")
        raise HTTPException(status_code=500, detail=str(e))
