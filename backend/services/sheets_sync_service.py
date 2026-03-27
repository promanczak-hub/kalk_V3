"""
Google Sheets → Supabase live sync service.

Architecture:
  - SheetsSyncService: fetches sheet data via gspread (service account auth)
  - SyncMapping: Pydantic model describing how a sheet column maps to a DB column
  - sync_sheet_to_table(): validates & upserts data into Supabase

Auth: uses a Google Service Account JSON key (path: GOOGLE_SA_KEY_PATH in env).
The service account must be shared (Editor or Viewer) on the target spreadsheet.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from pydantic import BaseModel, Field

from core.database import supabase

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ── Pydantic models ────────────────────────────────────────────────────────


class ColumnMapping(BaseModel):
    """Maps one spreadsheet column to one database column."""

    sheet_col: str = Field(description="Column header in Google Sheet")
    db_col: str = Field(description="Column name in Supabase table")
    transform: str = Field(
        default="str",
        description="Type cast: 'str' | 'int' | 'float' | 'bool'",
    )


class SyncMapping(BaseModel):
    """Full mapping spec: one sheet tab → one DB table."""

    spreadsheet_id: str
    sheet_name: str
    db_table: str
    column_mappings: list[ColumnMapping]
    upsert_conflict_column: str = Field(
        default="id",
        description="Column used as conflict key for upsert",
    )
    skip_rows: int = Field(
        default=0,
        description="Number of header rows to skip after the first",
    )


class SyncReport(BaseModel):
    """Result of one sync operation."""

    status: str
    table: str
    sheet: str
    rows_fetched: int = 0
    rows_upserted: int = 0
    rows_skipped: int = 0
    errors: list[str] = Field(default_factory=list)
    snapshot_version: int | None = None


class SheetInfo(BaseModel):
    """Metadata about one worksheet tab."""

    title: str
    row_count: int
    col_count: int
    headers: list[str]


class SpreadsheetInfo(BaseModel):
    """Available sheets in a spreadsheet."""

    spreadsheet_id: str
    title: str
    sheets: list[SheetInfo]


# ── Auth ───────────────────────────────────────────────────────────────────


def _build_gspread_client() -> gspread.Client:
    """Build authenticated gspread client from service account key."""
    key_path = os.environ.get("GOOGLE_SA_KEY_PATH", "")
    key_json_str = os.environ.get("GOOGLE_SA_KEY_JSON", "")

    if key_json_str:
        key_data = json.loads(key_json_str)
        creds = Credentials.from_service_account_info(key_data, scopes=_SCOPES)
    elif key_path and os.path.isfile(key_path):
        creds = Credentials.from_service_account_file(key_path, scopes=_SCOPES)
    else:
        raise RuntimeError(
            "Brak klucza Google Service Account. "
            "Ustaw GOOGLE_SA_KEY_PATH lub GOOGLE_SA_KEY_JSON w .env"
        )

    return gspread.authorize(creds)


# ── Core service ───────────────────────────────────────────────────────────


def inspect_spreadsheet(spreadsheet_id: str) -> SpreadsheetInfo:
    """
    Returns metadata about all tabs in a spreadsheet.
    Used by frontend to let the user pick which sheet maps to which table.
    """
    gc = _build_gspread_client()
    ss = gc.open_by_key(spreadsheet_id)

    sheets: list[SheetInfo] = []
    for ws in ss.worksheets():
        try:
            all_values = ws.get_all_values()
            if not all_values:
                headers: list[str] = []
            else:
                headers = [str(h).strip() for h in all_values[0] if str(h).strip()]
            sheets.append(
                SheetInfo(
                    title=ws.title,
                    row_count=ws.row_count,
                    col_count=ws.col_count,
                    headers=headers,
                )
            )
        except Exception as exc:
            logger.warning("Nie można odczytać arkusza '%s': %s", ws.title, exc)

    return SpreadsheetInfo(
        spreadsheet_id=spreadsheet_id,
        title=ss.title,
        sheets=sheets,
    )


def _cast_value(raw: Any, transform: str) -> Any:
    """Type-cast a cell value. Returns None on blank/error."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        if transform == "int":
            return int(float(str(raw).replace(",", ".")))
        if transform == "float":
            return float(str(raw).replace(",", "."))
        if transform == "bool":
            return str(raw).strip().lower() in ("1", "true", "tak", "yes")
        return str(raw).strip()
    except (ValueError, TypeError):
        return None


def _fetch_sheet_rows(
    gc: gspread.Client,
    mapping: SyncMapping,
) -> list[dict[str, Any]]:
    """Fetch and transform rows from Google Sheets according to mapping."""
    ss = gc.open_by_key(mapping.spreadsheet_id)
    ws = ss.worksheet(mapping.sheet_name)
    all_values = ws.get_all_values()

    if len(all_values) < 1:
        raise ValueError(f"Arkusz '{mapping.sheet_name}' jest pusty")

    header_row = [str(h).strip() for h in all_values[0]]
    data_rows = all_values[1 + mapping.skip_rows :]

    # Build index: sheet_col → column index in header
    col_index: dict[str, int] = {}
    for cm in mapping.column_mappings:
        if cm.sheet_col not in header_row:
            raise ValueError(
                f"Kolumna '{cm.sheet_col}' nie istnieje w arkuszu '{mapping.sheet_name}'. "
                f"Dostępne: {header_row}"
            )
        col_index[cm.sheet_col] = header_row.index(cm.sheet_col)

    result: list[dict[str, Any]] = []
    for row in data_rows:
        record: dict[str, Any] = {}
        is_blank = True
        for cm in mapping.column_mappings:
            idx = col_index[cm.sheet_col]
            raw = row[idx] if idx < len(row) else ""
            casted = _cast_value(raw, cm.transform)
            record[cm.db_col] = casted
            if casted is not None:
                is_blank = False
        if not is_blank:
            result.append(record)

    return result


def sync_sheet_to_table(mapping: SyncMapping) -> SyncReport:
    """
    Main sync function: fetch from Google Sheets → upsert into Supabase.

    Steps:
    1. Authenticate with Google
    2. Fetch all rows from the specified sheet tab
    3. Apply column mapping + type casts
    4. Create a pre-sync snapshot (via config_table_versions)
    5. Upsert into Supabase (conflict on upsert_conflict_column)
    """
    report = SyncReport(
        status="pending",
        table=mapping.db_table,
        sheet=mapping.sheet_name,
    )

    try:
        gc = _build_gspread_client()
        rows = _fetch_sheet_rows(gc, mapping)
        report.rows_fetched = len(rows)

        if not rows:
            report.status = "empty"
            logger.warning(
                "Arkusz '%s' nie zwrócił żadnych wierszy", mapping.sheet_name
            )
            return report

        # Pre-sync snapshot (best-effort — table may not be in config_table_versions)
        try:
            _create_sync_snapshot(mapping.db_table, mapping.sheet_name)
        except Exception as snap_exc:
            logger.warning("Snapshot pominięty: %s", snap_exc)

        # Upsert in batches of 200
        upserted = 0
        skipped = 0
        batch_size = 200

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            try:
                supabase.table(mapping.db_table).upsert(
                    batch,
                    on_conflict=mapping.upsert_conflict_column,
                ).execute()
                upserted += len(batch)
            except Exception as exc:
                err_msg = f"Batch {i // batch_size}: {exc}"
                logger.error("Błąd upsert: %s", err_msg)
                report.errors.append(err_msg)
                skipped += len(batch)

        report.rows_upserted = upserted
        report.rows_skipped = skipped
        report.status = "success" if not report.errors else "partial"

        logger.info(
            "Sync '%s' → '%s': %d upserted, %d skipped, %d errors",
            mapping.sheet_name,
            mapping.db_table,
            upserted,
            skipped,
            len(report.errors),
        )

    except Exception as exc:
        logger.exception("Sync failed: %s → %s", mapping.sheet_name, mapping.db_table)
        report.status = "error"
        report.errors.append(str(exc))

    return report


def _create_sync_snapshot(table_name: str, sheet_name: str) -> None:
    """Create a pre-sync snapshot in config_table_versions."""
    from api.config_crud_routes import _create_snapshot  # lazy import

    _create_snapshot(
        table_name,
        label=f"Auto: przed sync z Google Sheets '{sheet_name}'",
        created_by="sheets_sync",
    )
