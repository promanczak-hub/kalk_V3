from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
from core.database import supabase

router = APIRouter(prefix="/kalkulacje", tags=["kalkulacje"])


class CreateKalkulacjaRequest(BaseModel):
    stan_json: dict


class KalkulacjaResponse(BaseModel):
    id: str
    numer_kalkulacji: str
    status: str
    dane_pojazdu: Optional[str]
    cena_netto: Optional[float]
    created_at: str
    updated_at: str
    stan_json: Optional[dict] = None


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


@router.get("", response_model=List[KalkulacjaResponse])
def get_kalkulacje():
    try:
        res = (
            supabase.table("ltr_kalkulacje")
            .select(
                "id, numer_kalkulacji, status, dane_pojazdu, cena_netto, created_at, updated_at"
            )
            .order("created_at", desc=True)
            .execute()
        )
        return res.data
    except Exception as e:
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
        )

        # 3. Call Calculation Engine
        engine = LTRKalkulator(input_data=calc_input, settings=settings)
        matrix = engine.build_matrix()

        return {"status": "success", "vehicle_id": vehicle_id, "matrix": matrix}
    except Exception as e:
        print(f"Matrix Engine Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
