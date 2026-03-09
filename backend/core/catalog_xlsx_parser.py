"""Parse XLSX files for the full spreadsheet viewer in frontend.

Converts openpyxl workbook into JSON-serializable sheet data
with cell values, background colors, and merge ranges.
"""

from __future__ import annotations

import io
import logging
from typing import Any

import openpyxl
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# Max rows/cols to prevent memory issues on huge files
_MAX_ROWS = 500
_MAX_COLS = 50


def _color_to_hex(color: Any) -> str | None:
    """Convert openpyxl color to hex string."""
    if color is None:
        return None
    if hasattr(color, "rgb") and color.rgb and color.rgb != "00000000":
        rgb = str(color.rgb)
        if len(rgb) == 8:
            return f"#{rgb[2:]}"
        if len(rgb) == 6:
            return f"#{rgb}"
    return None


def _cell_value(cell: Any) -> str | int | float | bool | None:
    """Extract cell value as JSON-safe type."""
    val = cell.value
    if val is None:
        return None
    if isinstance(val, (int, float, bool)):
        return val
    return str(val)


def parse_xlsx_for_viewer(
    file_bytes: bytes,
) -> list[dict[str, Any]]:
    """Parse XLSX into structured data for frontend viewer.

    Returns list of sheets, each containing:
    - name: sheet title
    - rows: 2D array of cell objects {v, bg, bold, colspan, rowspan}
    - col_widths: list of column widths
    - merge_ranges: list of merged cell ranges
    - row_count: total rows
    - col_count: total columns
    """
    wb = openpyxl.load_workbook(
        io.BytesIO(file_bytes),
        read_only=False,
        data_only=True,
    )

    sheets: list[dict[str, Any]] = []

    for ws in wb.worksheets:
        # Determine dimensions
        max_row = min(ws.max_row or 1, _MAX_ROWS)
        max_col = min(ws.max_column or 1, _MAX_COLS)

        # Collect merged cell ranges
        merges: list[dict[str, Any]] = []
        merged_cells: set[tuple[int, int]] = set()
        merge_origins: dict[tuple[int, int], dict[str, int]] = {}

        for merge_range in ws.merged_cells.ranges:
            min_r, min_c = merge_range.min_row, merge_range.min_col
            max_r, max_c = merge_range.max_row, merge_range.max_col
            merges.append(
                {
                    "range": str(merge_range),
                    "startRow": min_r - 1,
                    "startCol": min_c - 1,
                    "endRow": max_r - 1,
                    "endCol": max_c - 1,
                }
            )
            colspan = max_c - min_c + 1
            rowspan = max_r - min_r + 1
            merge_origins[(min_r, min_c)] = {
                "colspan": colspan,
                "rowspan": rowspan,
            }
            for r in range(min_r, max_r + 1):
                for c in range(min_c, max_c + 1):
                    if (r, c) != (min_r, min_c):
                        merged_cells.add((r, c))

        # Build rows
        rows: list[list[dict[str, Any] | None]] = []
        for row_idx in range(1, max_row + 1):
            row_data: list[dict[str, Any] | None] = []
            for col_idx in range(1, max_col + 1):
                if (row_idx, col_idx) in merged_cells:
                    row_data.append(None)
                    continue

                cell = ws.cell(row=row_idx, column=col_idx)
                cell_obj: dict[str, Any] = {
                    "v": _cell_value(cell),
                }

                # Background color
                fill = cell.fill
                if isinstance(fill, PatternFill) and fill.fgColor:
                    bg = _color_to_hex(fill.fgColor)
                    if bg:
                        cell_obj["bg"] = bg

                # Bold
                if cell.font and cell.font.bold:
                    cell_obj["bold"] = True

                # Merge spans
                merge_info = merge_origins.get((row_idx, col_idx))
                if merge_info:
                    if merge_info["colspan"] > 1:
                        cell_obj["colspan"] = merge_info["colspan"]
                    if merge_info["rowspan"] > 1:
                        cell_obj["rowspan"] = merge_info["rowspan"]

                row_data.append(cell_obj)
            rows.append(row_data)

        # Column widths
        col_widths: list[float] = []
        for col_idx in range(1, max_col + 1):
            letter = get_column_letter(col_idx)
            dim = ws.column_dimensions.get(letter)
            width = dim.width if dim and dim.width else 10.0
            col_widths.append(float(width))

        sheets.append(
            {
                "name": ws.title,
                "rows": rows,
                "col_widths": col_widths,
                "merge_ranges": merges,
                "row_count": max_row,
                "col_count": max_col,
            }
        )

    wb.close()
    return sheets
