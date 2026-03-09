"""CRUD + XLSX export/import for universal feature categories & features.

Endpoints under /api/features/admin/...
Operates on reverse_search schema tables.
"""

from __future__ import annotations

import io
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Protection
from openpyxl.utils import get_column_letter
from pydantic import BaseModel

from core.database import supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Features Admin"])

# ── Styling constants ────────────────────────────────────────────
_HEADER_FILL = PatternFill(
    start_color="D9D9D9",
    end_color="D9D9D9",
    fill_type="solid",
)
_HEADER_FONT = Font(bold=True, size=11)
_ID_FILL = PatternFill(
    start_color="FFFFCC",
    end_color="FFFFCC",
    fill_type="solid",
)
_LOCKED = Protection(locked=True)
_UNLOCKED = Protection(locked=False)
_ID_COLUMNS = {"id", "created_at", "updated_at"}
_SHEET_PASSWORD = "kalk_v3_features"


# ── Pydantic Models ──────────────────────────────────────────────


class CategoryIn(BaseModel):
    """Payload for creating/updating a category."""

    id: Optional[int] = None
    category_key: str
    display_name: str
    vehicle_scope: str = "both"
    sort_order: int = 100
    is_active: bool = True


class FeatureIn(BaseModel):
    """Payload for creating/updating a feature."""

    id: Optional[int] = None
    category_id: str
    feature_key: str
    display_name: str
    feature_type: str = "boolean"
    vehicle_scope: str = "both"
    sort_order: int = 100
    is_active: bool = True
    source_column_index: Optional[int] = None
    description: Optional[str] = None
    applicable_body_types: Optional[list[str]] = None


class ImportReport(BaseModel):
    """Result of an XLSX import operation."""

    status: str
    updated: int = 0
    inserted: int = 0
    skipped: int = 0
    errors: List[str] = []


# ── Helpers ──────────────────────────────────────────────────────


def _sb_rs():
    """Shortcut for reverse_search schema client."""
    return supabase.schema("reverse_search")


def _build_xlsx(
    rows: list[dict[str, Any]],
    sheet_title: str,
) -> io.BytesIO:
    """Build protected XLSX workbook from row dicts."""
    wb = Workbook()
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet()
    ws.title = sheet_title[:31]

    if not rows:
        ws.append(["Brak danych"])
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return out

    headers = list(rows[0].keys())
    id_cols = {i for i, h in enumerate(headers) if h.lower() in _ID_COLUMNS}

    for col_i, hdr in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_i, value=hdr)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.protection = _LOCKED
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    for row_i, rd in enumerate(rows, 2):
        for col_i, hdr in enumerate(headers, 1):
            val = rd.get(hdr)
            # Serialize lists to comma-separated strings
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            cell = ws.cell(row=row_i, column=col_i, value=val)
            if (col_i - 1) in id_cols:
                cell.fill = _ID_FILL
                cell.protection = _LOCKED
            else:
                cell.protection = _UNLOCKED

    for col_i in range(1, len(headers) + 1):
        max_len = len(str(headers[col_i - 1]))
        for row_i in range(2, min(len(rows) + 2, 52)):
            cv = ws.cell(row=row_i, column=col_i).value
            if cv is not None:
                max_len = max(max_len, len(str(cv)))
        ws.column_dimensions[get_column_letter(col_i)].width = min(
            max_len + 3,
            40,
        )

    ws.protection.sheet = True
    ws.protection.password = _SHEET_PASSWORD
    ws.protection.enable()

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out


# ══════════════════════════════════════════════════════════════════
# CATEGORIES CRUD
# ══════════════════════════════════════════════════════════════════


@router.get("/features/admin/categories")
async def list_categories() -> list[dict[str, Any]]:
    """List all feature categories."""
    resp = (
        _sb_rs()
        .table("universal_feature_categories")
        .select("*")
        .order("sort_order")
        .execute()
    )
    return resp.data or []


@router.post("/features/admin/categories")
async def upsert_category(item: CategoryIn) -> dict[str, Any]:
    """Create or update a feature category."""
    data = item.model_dump(exclude_none=True)
    try:
        resp = (
            _sb_rs()
            .table("universal_feature_categories")
            .upsert(data, on_conflict="category_key")
            .execute()
        )
        return resp.data[0] if resp.data else {}
    except Exception as exc:
        logger.exception("Category upsert failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/features/admin/categories/{category_id}")
async def delete_category(category_id: int) -> dict[str, str]:
    """Delete a feature category."""
    try:
        _sb_rs().table("universal_feature_categories").delete().eq(
            "id",
            category_id,
        ).execute()
        return {"status": "deleted"}
    except Exception as exc:
        logger.exception("Category delete failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ══════════════════════════════════════════════════════════════════
# FEATURES CRUD
# ══════════════════════════════════════════════════════════════════


@router.get("/features/admin/features")
async def list_features(
    category_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """List all features, optionally filtered by category."""
    q = _sb_rs().table("universal_features").select("*").order("sort_order")
    if category_id is not None:
        q = q.eq("category_id", category_id)
    return q.execute().data or []


@router.post("/features/admin/features")
async def upsert_feature(item: FeatureIn) -> dict[str, Any]:
    """Create or update a feature."""
    data = item.model_dump(exclude_none=True)
    try:
        resp = (
            _sb_rs()
            .table("universal_features")
            .upsert(data, on_conflict="feature_key")
            .execute()
        )
        return resp.data[0] if resp.data else {}
    except Exception as exc:
        logger.exception("Feature upsert failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/features/admin/features/{feature_id}")
async def delete_feature(feature_id: int) -> dict[str, str]:
    """Delete a feature."""
    try:
        _sb_rs().table("universal_features").delete().eq(
            "id",
            feature_id,
        ).execute()
        return {"status": "deleted"}
    except Exception as exc:
        logger.exception("Feature delete failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ══════════════════════════════════════════════════════════════════
# XLSX EXPORT
# ══════════════════════════════════════════════════════════════════


@router.get("/features/admin/categories/export-xlsx")
async def export_categories_xlsx() -> StreamingResponse:
    """Export all categories as protected XLSX."""
    rows = (
        _sb_rs()
        .table("universal_feature_categories")
        .select("*")
        .order("sort_order")
        .execute()
    ).data or []
    xlsx = _build_xlsx(rows, "Kategorie Cech")
    return StreamingResponse(
        xlsx,
        headers={
            "Content-Disposition": (
                "attachment; filename=feature_categories_export.xlsx"
            ),
        },
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


@router.get("/features/admin/features/export-xlsx")
async def export_features_xlsx() -> StreamingResponse:
    """Export all features as protected XLSX."""
    rows = (
        _sb_rs().table("universal_features").select("*").order("sort_order").execute()
    ).data or []
    xlsx = _build_xlsx(rows, "Cechy Pojazdow")
    return StreamingResponse(
        xlsx,
        headers={
            "Content-Disposition": ("attachment; filename=features_export.xlsx"),
        },
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


# ══════════════════════════════════════════════════════════════════
# XLSX IMPORT
# ══════════════════════════════════════════════════════════════════


@router.post("/features/admin/categories/import-xlsx")
async def import_categories_xlsx(
    file: UploadFile = File(...),
) -> ImportReport:
    """Import categories from XLSX. Upserts by category_key."""
    return await _import_xlsx(
        file,
        table="universal_feature_categories",
        upsert_key="category_key",
    )


@router.post("/features/admin/features/import-xlsx")
async def import_features_xlsx(
    file: UploadFile = File(...),
) -> ImportReport:
    """Import features from XLSX. Upserts by feature_key."""
    return await _import_xlsx(
        file,
        table="universal_features",
        upsert_key="feature_key",
    )


async def _import_xlsx(
    file: UploadFile,
    table: str,
    upsert_key: str,
) -> ImportReport:
    """Generic XLSX import into a reverse_search table."""
    try:
        contents = await file.read()
        wb = load_workbook(io.BytesIO(contents))
        ws = wb.active
        if ws is None:
            raise HTTPException(
                status_code=400,
                detail="Plik XLSX nie zawiera arkuszy",
            )

        headers: list[str] = []
        for cell in ws[1]:
            if cell.value is not None:
                headers.append(str(cell.value))
        if not headers:
            raise HTTPException(
                status_code=400,
                detail="Brak nagłówków w pliku XLSX",
            )

        updated = 0
        inserted = 0
        skipped = 0
        errors: list[str] = []

        for row_idx, row in enumerate(
            ws.iter_rows(min_row=2),
            start=2,
        ):
            row_data: dict[str, Any] = {}
            is_empty = True
            for col_idx, cell in enumerate(row):
                if col_idx >= len(headers):
                    break
                hdr = headers[col_idx]
                val = cell.value

                if hdr == "applicable_body_types" and val is not None:
                    if isinstance(val, str):
                        val = [v.strip() for v in val.split(",") if v.strip()]
                    elif not val:  # Handle empty string or similar
                        val = None

                if val is not None:
                    is_empty = False
                row_data[hdr] = val

            if is_empty:
                skipped += 1
                continue

            # Clean ID columns for insert
            clean = {k: v for k, v in row_data.items() if k.lower() not in _ID_COLUMNS}
            key_val = clean.get(upsert_key)
            if not key_val:
                errors.append(
                    f"Wiersz {row_idx}: brak wartości {upsert_key}",
                )
                continue

            try:
                _sb_rs().table(table).upsert(
                    clean,
                    on_conflict=upsert_key,
                ).execute()
                # We can't easily distinguish insert/update here
                inserted += 1
            except Exception as row_exc:
                errors.append(f"Wiersz {row_idx}: {row_exc}")

        return ImportReport(
            status="success",
            updated=updated,
            inserted=inserted,
            skipped=skipped,
            errors=errors,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("XLSX import failed for %s", table)
        raise HTTPException(status_code=500, detail=str(exc))
