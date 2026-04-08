"""Parser for tender criteria Excel/CSV uploads.

Converts uploaded Excel/CSV files into TenderEvaluateRequest.

Expected columns:
- Feature_Key (required): technical_key matching universal_features
- Operator (required): >=, <=, >, <, =, !=, IN
- Value (required): target value
- Priority (optional): MUST, SHOULD, NICE (default: MUST)
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

from core.mdm_models import (
    TenderCriterion,
    TenderEvaluateRequest,
    TenderPriority,
)

logger = logging.getLogger(__name__)

# Column name aliases (case-insensitive matching)
_KEY_ALIASES = {
    "feature_key",
    "technical_key",
    "requirement_key",
    "key",
    "cecha",
}
_OPERATOR_ALIASES = {"operator", "op", "comparison", "warunek"}
_VALUE_ALIASES = {"value", "val", "wartość", "wartosc", "threshold"}
_PRIORITY_ALIASES = {"priority", "priorytet", "importance", "level"}


def _find_column(headers: list[str], aliases: set[str]) -> int | None:
    """Find column index by checking against known aliases."""
    for idx, h in enumerate(headers):
        if h.strip().lower() in aliases:
            return idx
    return None


def _parse_value(
    raw: str,
) -> float | str | bool | list[str]:
    """Parse a raw string value into the appropriate type."""
    stripped = raw.strip()

    # Boolean
    if stripped.upper() in ("TRUE", "TAK", "YES", "1"):
        return True
    if stripped.upper() in ("FALSE", "NIE", "NO", "0"):
        return False

    # List (comma-separated for IN operator)
    if "," in stripped:
        return [v.strip() for v in stripped.split(",")]

    # Numeric
    try:
        return float(stripped)
    except ValueError:
        return stripped


def _parse_priority(raw: str | None) -> TenderPriority:
    """Parse priority string to enum."""
    if not raw:
        return TenderPriority.MUST

    mapping = {
        "MUST": TenderPriority.MUST,
        "REQUIRED": TenderPriority.MUST,
        "WYMAGANE": TenderPriority.MUST,
        "SHOULD": TenderPriority.SHOULD,
        "PREFERRED": TenderPriority.SHOULD,
        "PREFEROWANE": TenderPriority.SHOULD,
        "NICE": TenderPriority.NICE,
        "OPTIONAL": TenderPriority.NICE,
        "OPCJONALNE": TenderPriority.NICE,
    }
    return mapping.get(raw.strip().upper(), TenderPriority.MUST)


def parse_tender_csv(
    content: str,
    delimiter: str = ";",
) -> TenderEvaluateRequest:
    """Parse CSV string into TenderEvaluateRequest.

    Raises ValueError if required columns are missing or no valid rows.
    """
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)

    rows = list(reader)
    if len(rows) < 2:
        msg = "CSV must contain at least a header row and one data row"
        raise ValueError(msg)

    # Filter out comment rows (starting with #)
    data_rows = [r for r in rows if r and not r[0].strip().startswith("#")]
    if len(data_rows) < 2:
        msg = "No data rows found (excluding comments)"
        raise ValueError(msg)

    headers = [h.strip().lower() for h in data_rows[0]]

    key_col = _find_column(headers, _KEY_ALIASES)
    op_col = _find_column(headers, _OPERATOR_ALIASES)
    val_col = _find_column(headers, _VALUE_ALIASES)
    pri_col = _find_column(headers, _PRIORITY_ALIASES)

    if key_col is None:
        msg = f"Missing required column: Feature_Key. Found: {headers}"
        raise ValueError(msg)
    if op_col is None:
        msg = f"Missing required column: Operator. Found: {headers}"
        raise ValueError(msg)
    if val_col is None:
        msg = f"Missing required column: Value. Found: {headers}"
        raise ValueError(msg)

    criteria: list[TenderCriterion] = []
    errors: list[str] = []

    for row_idx, row in enumerate(data_rows[1:], start=2):
        if not row or len(row) <= max(key_col, op_col, val_col):
            continue

        feature_key = row[key_col].strip()
        operator = row[op_col].strip()
        raw_value = row[val_col].strip()

        if not feature_key or not operator or not raw_value:
            continue

        # Validate operator
        valid_ops = {">=", "<=", ">", "<", "=", "!=", "IN"}
        if operator.upper() not in valid_ops:
            errors.append(
                f"Row {row_idx}: Invalid operator '{operator}'. Valid: {valid_ops}"
            )
            continue

        priority_raw = (
            row[pri_col].strip() if pri_col is not None and len(row) > pri_col else None
        )

        criteria.append(
            TenderCriterion(
                feature_key=feature_key,
                operator=operator.upper() if operator.upper() == "IN" else operator,
                value=_parse_value(raw_value),
                priority=_parse_priority(priority_raw),
            )
        )

    if errors:
        logger.warning("Parse errors in tender CSV: %s", errors)

    if not criteria:
        msg = "No valid criteria found in CSV"
        raise ValueError(msg)

    logger.info("Parsed %d tender criteria from CSV", len(criteria))
    return TenderEvaluateRequest(criteria=criteria)


def parse_tender_excel(file_path: Path) -> TenderEvaluateRequest:
    """Parse Excel file (.xlsx) into TenderEvaluateRequest.

    Uses openpyxl for .xlsx files.

    Raises ValueError if parsing fails.
    """
    try:
        import openpyxl
    except ImportError as exc:
        msg = "openpyxl is required for Excel parsing: pip install openpyxl"
        raise ImportError(msg) from exc

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    if ws is None:
        msg = "Excel file has no active worksheet"
        raise ValueError(msg)

    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])

    wb.close()

    if not rows:
        msg = "Excel file is empty"
        raise ValueError(msg)

    # Convert to CSV string and reuse CSV parser
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    for row in rows:
        writer.writerow(row)

    return parse_tender_csv(output.getvalue(), delimiter=";")
