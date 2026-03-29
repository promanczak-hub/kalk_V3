import logging
from typing import Any, Dict, cast
from fastapi import APIRouter, HTTPException

from api.schemas.calculator import CalculatorInput
from core.database import supabase
from core.models import ControlCenterSettings
from domain.calculations.service import CalculationService

router = APIRouter(prefix="/api/ltr", tags=["LTR Manual Calculator"])


@router.post("/calculate-manual")
def calculate_manual(data: CalculatorInput) -> Dict[str, Any]:
    """
    Wykonuje pełną kalkulację LTR dla danych wprowadzonych ręcznie (Manual Calculator).
    Zwraca podsumowanie oraz pełny 12-krokowy ślad rewizyjny (trace).
    """
    try:
        # 1. Pobierz ustawienia globalne z Control Center
        response = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Control center settings not found"
            )

        response_data = cast(Any, response.data[0])
        settings = ControlCenterSettings(**response_data)

        # 2. Uruchom serwis kalkulacyjny
        calc_service = CalculationService(data=data, settings=settings)

        # generate_single_trace zwraca (matrix_cells, trace_data)
        matrix_cells, trace_data = calc_service.generate_single_trace()

        # Wyciągnij finalną ratę (total_rent) z trace_data lub matrix_cells
        # W trace_data ostatni krok to zazwyczaj Budżet Mktg, ale wynik końcowy to suma/wynik z kroku Stawka
        total_rent = 0.0
        for step in trace_data:
            if step.get("krok") == "11. STAWKA MIESIĘCZNA NETTO":
                total_rent = step.get("wynik", 0.0)
                break

        if total_rent == 0.0 and trace_data:
            # Fallback do ostatniego kroku jeśli nie znaleziono po nazwie
            total_rent = trace_data[-1].get("wynik", 0.0)

        return {
            "status": "success",
            "total_rent": total_rent,
            "steps": trace_data,
            "summary": {
                "base_price_net": data.base_price_net,
                "total_discount_net": data.base_price_net * data.discount_pct,
                "final_price_net": data.base_price_net * (1 - data.discount_pct),
            },
        }

    except ValueError as ve:
        logging.warning(f"Błąd walidacji w kalkulacji manualnej: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Błąd wewnętrzny w kalkulacji manualnej: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
