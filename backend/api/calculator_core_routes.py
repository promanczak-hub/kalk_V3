import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from api.schemas.calculator import CalculatorInput
from core.control_center import fetch_control_center_settings

router = APIRouter()


@router.post("/calculate-matrix")
def calculate_matrix(data: CalculatorInput) -> Dict[str, Any]:
    try:
        from core.calculation_service import CalculationService

        settings = fetch_control_center_settings()

        # Wykorzystanie wzorca UseCase/Service z domeny calculations
        calc_service = CalculationService(data=data, settings=settings)
        matrix_cells = calc_service.calculate_matrix()

        # Opcjonalny zrzut do konsoli, izolowany wewnątrz serwisu
        calc_service.print_terminal_trace(matrix_cells)

        return {
            "status": "success",
            "message": "Matrix calculation completed successfully",
            "cells": matrix_cells,
        }
    except ValueError as ve:
        logging.warning(f"Validation error in calculate-matrix: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Internal error in calculate-matrix: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-trace")
def calculate_trace(data: CalculatorInput) -> Dict[str, Any]:
    """Przelicza matrycę i zwraca pełen obiekt ze śladem diagnostycznym."""
    try:
        from core.calculation_service import CalculationService

        settings = fetch_control_center_settings()

        calc_service = CalculationService(data=data, settings=settings)
        matrix_cells, trace_data = calc_service.generate_single_trace()

        return {
            "status": "success",
            "message": "Trace generated successfully",
            "cells": matrix_cells,
            "calculation_trace": trace_data,
        }
    except ValueError as ve:
        logging.warning(f"Validation error in calculate-trace: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Internal error in calculate-trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match-body-type", tags=["Calculator"])
def match_body_type_endpoint(
    body_style_raw: str = "",
) -> Dict[str, Any]:
    """Fuzzy-match raw body_style → body_types with score."""
    from core.body_type_matcher import match_body_type

    result = match_body_type(body_style_raw)
    return {
        "matched_body_type_id": result.matched_body_type_id,
        "matched_name": result.matched_name,
        "vehicle_class": result.vehicle_class,
        "score": result.score,
        "match_method": result.match_method,
        "raw_input": result.raw_input,
    }

