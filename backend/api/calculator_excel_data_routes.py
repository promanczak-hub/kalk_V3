from typing import Any, Dict, List, Optional, cast
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import supabase

router = APIRouter()


class CalculatorExcelData(BaseModel):
    id: Optional[str] = None
    sheet_name: str
    row_data: List[Dict[str, Any]]
    updated_at: Optional[str] = None


@router.get("/calculator-excel-data", tags=["Calculator Excel Data"])
async def get_calculator_excel_data() -> List[CalculatorExcelData]:
    try:
        response = (
            supabase.table("calculator_excel_data")
            .select("*")
            .order("sheet_name")
            .execute()
        )
        if not response.data:
            return []
        response_data = cast(Any, response.data)
        return [CalculatorExcelData(**row) for row in response_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculator-excel-data", tags=["Calculator Excel Data"])
async def update_calculator_excel_data(
    data: CalculatorExcelData,
) -> CalculatorExcelData:
    try:
        payload = data.model_dump(exclude_unset=True)
        if not payload.get("id"):
            payload.pop("id", None)

        response = (
            supabase.table("calculator_excel_data")
            .upsert(payload, on_conflict="sheet_name")
            .execute()
        )

        if hasattr(response, "error") and response.error:
            raise HTTPException(
                status_code=500, detail=f"Failed to update excel data: {response.error}"
            )

        response_data = cast(Any, response.data[0])
        return CalculatorExcelData(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
