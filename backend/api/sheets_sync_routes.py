"""
FastAPI routes for Google Sheets → Supabase sync.

Endpoints:
  GET  /api/sheets/inspect?spreadsheet_id=...  → list tabs + headers
  POST /api/sheets/sync                         → run sync with mapping
  GET  /api/sheets/tables                       → list allowed DB tables
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.config_crud_routes import ALLOWED_TABLES
from services.sheets_sync_service import (
    ColumnMapping,
    SpreadsheetInfo,
    SyncMapping,
    SyncReport,
    inspect_spreadsheet,
    sync_sheet_to_table,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sheets", tags=["Google Sheets Sync"])


# ── Models ─────────────────────────────────────────────────────────────────


class SyncRequest(BaseModel):
    spreadsheet_id: str
    sheet_name: str
    db_table: str
    column_mappings: list[ColumnMapping]
    upsert_conflict_column: str = "id"
    skip_rows: int = 0


class AvailableTable(BaseModel):
    table_name: str
    label: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/tables", response_model=list[AvailableTable])
def list_syncable_tables() -> list[AvailableTable]:
    """List all DB tables that can be synced from Google Sheets."""
    return [
        AvailableTable(table_name=k, label=v) for k, v in sorted(ALLOWED_TABLES.items())
    ]


@router.get("/inspect", response_model=SpreadsheetInfo)
def inspect_sheet(spreadsheet_id: str) -> SpreadsheetInfo:
    """
    Returns all worksheet tabs and their column headers.
    Used by frontend to build the column mapping UI.
    """
    try:
        return inspect_spreadsheet(spreadsheet_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to inspect spreadsheet %s", spreadsheet_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sync", response_model=SyncReport)
def run_sync(body: SyncRequest) -> SyncReport:
    """
    Execute a sync: pull data from Google Sheet, upsert into Supabase.
    Validates db_table against whitelist before executing.
    """
    if body.db_table not in ALLOWED_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Tabela '{body.db_table}' nie jest na liście dozwolonych. "
            f"Użyj GET /api/sheets/tables aby zobaczyć dostępne.",
        )

    mapping = SyncMapping(
        spreadsheet_id=body.spreadsheet_id,
        sheet_name=body.sheet_name,
        db_table=body.db_table,
        column_mappings=body.column_mappings,
        upsert_conflict_column=body.upsert_conflict_column,
        skip_rows=body.skip_rows,
    )

    report = sync_sheet_to_table(mapping)

    if report.status == "error":
        logger.error(
            "Sync error for %s → %s: %s",
            body.sheet_name,
            body.db_table,
            report.errors,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Sync zakończony błędem dla '{body.db_table}'",
                "errors": report.errors,
            },
        )

    return report
