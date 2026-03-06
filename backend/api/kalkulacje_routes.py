from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional, List, cast
from datetime import datetime
import uuid
import logging
from core.database import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kalkulacje", tags=["kalkulacje"])


class CreateKalkulacjaRequest(BaseModel):
    stan_json: dict


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
    dane_pojazdu: Optional[str]
    cena_netto: Optional[float]
    created_at: str
    updated_at: str
    stan_json: Optional[dict] = None


class KalkulacjaListItem(BaseModel):
    id: str
    numer_kalkulacji: str
    status: str
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

    data = {
        "numer_kalkulacji": numer_kalkulacji,
        "status": "szkic_vertex",
        "stan_json": req.stan_json,
        "dane_pojazdu": dane_pojazdu,
        "cena_netto": cena_netto,
    }

    try:
        res = supabase.table("ltr_kalkulacje").insert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Błąd przy zapisie do bazy.")
        return res.data[0]
    except Exception as e:
        print(f"Db Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _extract_list_fields(row: Dict[str, Any]) -> KalkulacjaListItem:
    """Extract enriched fields from stan_json for list view."""
    sj = cast(Dict[str, Any], row.get("stan_json") or {})
    vehicle_mapped = cast(Dict[str, Any], sj.get("vehicle_mapped") or {})
    discount_block = cast(Dict[str, Any], sj.get("discount") or {})

    factory_opts = sj.get("factory_options") or []
    service_opts = sj.get("service_options") or []

    return KalkulacjaListItem(
        id=row["id"],
        numer_kalkulacji=row["numer_kalkulacji"],
        status=row.get("status", "szkic_vertex"),
        dane_pojazdu=row.get("dane_pojazdu"),
        cena_netto=row.get("cena_netto"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        body_type=vehicle_mapped.get("body_type"),
        fuel_type=vehicle_mapped.get("fuel_type"),
        discount_pct=discount_block.get("active_discount_pct"),
        options_count=len(factory_opts) + len(service_opts),
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

        new_data = {
            "numer_kalkulacji": new_numer,
            "status": "szkic_vertex",
            "stan_json": original.get("stan_json", {}),
            "dane_pojazdu": original.get("dane_pojazdu", "Kopia"),
            "cena_netto": original.get("cena_netto", 0.0),
        }

        insert_res = supabase.table("ltr_kalkulacje").insert(new_data).execute()
        if not insert_res.data:
            raise HTTPException(status_code=500, detail="Błąd duplikacji")
        return insert_res.data[0]
    except Exception as e:
        logger.exception("DUPLICATE /kalkulacje/%s failed", kalk_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{kalk_id}/status")
def update_kalkulacja_status(kalk_id: str, req: StatusUpdateRequest):
    """Update status of a kalkulacja (workflow transition)."""
    if req.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Nieprawidłowy status '{req.status}'. "
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


@router.post("/extract-matrix-v3/{vehicle_id}")
def generate_matrix_from_extracted_v3(vehicle_id: str, req: dict):
    from main import CalculatorInput, VehicleOptions
    from core.LTRKalkulator import LTRKalkulator

    try:
        # Reconstruct Input manually since frontend sends partial/simplified data
        cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not cc_res.data:
            raise HTTPException(status_code=500, detail="Brak ustawień CC")
        from typing import cast, Any, Dict
        from core.models import ControlCenterSettings

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
                )
            )

        # 2. Map Payload
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
            # Flagi kosztów dodatkowych (globalne kwoty z CC, tu ON/OFF per kalkulacja)
            add_gsm_subscription=req.get("add_gsm_subscription", True),
            add_hook_installation=req.get("add_hook_installation", False),
            add_grid_dismantling=req.get("add_grid_dismantling", False),
            add_registration=req.get("add_registration", True),
            add_sales_prep=req.get("add_sales_prep", True),
        )

        # 3. Call Calculation Engine
        engine = LTRKalkulator(input_data=calc_input, settings=settings)
        matrix = engine.build_matrix()

        return {"status": "success", "vehicle_id": vehicle_id, "matrix": matrix}
    except Exception as e:
        print(f"Matrix Engine Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug-pipeline/{vehicle_id}")
def debug_calculation_pipeline(vehicle_id: str, req: dict):
    from main import CalculatorInput, VehicleOptions
    from core.PipelineDebugger import PipelineDebugger
    from core.models import ControlCenterSettings
    from typing import cast, Any, Dict

    try:
        # Reconstruct Control Center Settings
        cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not cc_res.data:
            raise HTTPException(status_code=500, detail="Brak ustawień CC")

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
            # Flagi kosztów dodatkowych (globalne kwoty z CC, tu ON/OFF per kalkulacja)
            add_gsm_subscription=req.get("add_gsm_subscription", True),
            add_hook_installation=req.get("add_hook_installation", False),
            add_grid_dismantling=req.get("add_grid_dismantling", False),
            add_registration=req.get("add_registration", True),
            add_sales_prep=req.get("add_sales_prep", True),
        )

        # 3. Handle overrides and months for execution
        months = req.get("months", calc_input.okres_bazowy)
        overrides = req.get("overrides", {})

        # 4. Call Debugger Engine
        debugger = PipelineDebugger(input_data=calc_input, settings=settings)
        steps = debugger.calculate_steps(months=months, overrides=overrides)

        return {
            "status": "success",
            "vehicle_id": vehicle_id,
            "months": months,
            "steps": steps,
        }
    except Exception as e:
        print(f"Debugger Engine Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug-pipeline/{vehicle_id}/ask-ai")
def ask_ai_about_step(vehicle_id: str, req: AskAiRequest):
    from core.gemini_client import get_gemini_client
    import json

    try:
        client = get_gemini_client()

        prompt = f"""
Jesteś inżynierem-asystentem w systemie kalkulatora leasingowego. Użytkownik przegląda krok "{req.step_name}" w dziale Pipeline Debugger i zadał pytanie.
Oto kontekst tego kroku:
WEJŚCIA (Inputs):
{json.dumps(req.inputs, indent=2, ensure_ascii=False)}

WYJŚCIA (Outputs):
{json.dumps(req.outputs, indent=2, ensure_ascii=False)}

METADANE (Wzory i Źródła):
{json.dumps(req.metadata or {}, indent=2, ensure_ascii=False)}

Pytanie użytkownika:
{req.query}

Odpowiedz krótko i merytorycznie w języku polskim. Wyjaśnij dlaczego dany krok wyliczył taką wartość (np. zero, lub daną stawkę). Wskazuj na konkretne Wejścia (Inputs) lub Metadane (np. brak ustawień w bazie).
Bądź techniczny, przyjazny i konkretnie diagnozuj wynik. Używaj formatowania Markdown by wypunktować kluczowe powody.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return {"status": "success", "answer": response.text}
    except Exception as e:
        print(f"AI Debugger Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
