from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import supabase

router = APIRouter(tags=["Excel Drafts"])


class ColumnDef(BaseModel):
    field: str
    headerName: str
    width: Optional[int] = 150


class ExcelDraftSheet(BaseModel):
    id: Optional[int] = None
    sheet_name: str
    columns_def: List[Dict[str, Any]]
    data_rows: List[Dict[str, Any]]


class ExcelDraftUpdate(BaseModel):
    columns_def: List[Dict[str, Any]]
    data_rows: List[Dict[str, Any]]


@router.get("/excel-drafts", response_model=List[ExcelDraftSheet])
def get_all_excel_drafts():
    try:
        response = (
            supabase.table("excel_drafts")
            .select("id, sheet_name, columns_def, data_rows")
            .order("id")
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/excel-drafts/{sheet_name}", response_model=ExcelDraftSheet)
def get_excel_draft(sheet_name: str):
    try:
        response = (
            supabase.table("excel_drafts")
            .select("id, sheet_name, columns_def, data_rows")
            .eq("sheet_name", sheet_name)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Sheet not found")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/excel-drafts/{sheet_name}", response_model=ExcelDraftSheet)
def update_excel_draft(sheet_name: str, payload: ExcelDraftUpdate):
    try:
        # Check if exists
        check = (
            supabase.table("excel_drafts")
            .select("id")
            .eq("sheet_name", sheet_name)
            .execute()
        )
        if not check.data:
            raise HTTPException(status_code=404, detail="Sheet not found")

        record = {"columns_def": payload.columns_def, "data_rows": payload.data_rows}
        response = (
            supabase.table("excel_drafts")
            .update(record)
            .eq("sheet_name", sheet_name)
            .execute()
        )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
