"""MDM Sync: Google Sheet 'cechy' ↔ Supabase universal_features.

Bidirectional sync:
1. EXPORT: Dumps all DB features → Sheet (backfill)
2. IMPORT: Reads Sheet → upserts into DB (ongoing sync)

Uses feature_key as the primary sync identity.
Never deletes — only ADD / UPDATE.
"""

from __future__ import annotations

import logging
import os
import re

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from core.database import supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SHEET_NAME = "cechy"  # Tab name in the spreadsheet

# Column mapping: Sheet header → DB column
SHEET_TO_DB: dict[str, str] = {
    "Technical_Key": "feature_key",
    "Functional_Name": "display_name",
    "Category": "category",
    "Data_Type": "feature_type",
    "Unit_Source": "unit_source",
    "Unit_Target": "unit_target",
    "Transformation": "transformation",
    "Trigger_Keywords": "trigger_keywords",
    "Kategoria_Pojazdu": "applies_to_vehicle_categories",
    "Body_Context": "applies_to_body_subtypes",
    "Powertrain_Context": "applies_to_powertrains",
    "Drivetrain_Context": "applies_to_drivetrains",
    "Is_Derived": "is_derived",
    "Is_Contextual": "is_contextual",
    "Is_Filterable": "is_filterable",
}

# DB column → Sheet header (reverse for export)
DB_TO_SHEET: dict[str, str] = {v: k for k, v in SHEET_TO_DB.items()}

# Array columns — stored as JSON arrays in DB
_ARRAY_COLUMNS = {
    "applies_to_vehicle_categories",
    "applies_to_body_subtypes",
    "applies_to_powertrains",
    "applies_to_drivetrains",
    "trigger_keywords",
}


def _get_gspread_client() -> gspread.Client:
    """Authenticate with Google Sheets using service account."""
    key_path = os.environ.get(
        "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
    )
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)


def _parse_bool(val: str) -> bool:
    """Parse boolean-like string."""
    return val.strip().upper() in ("TRUE", "1", "TAK", "YES", "T")


def _parse_keywords(val: str) -> list[str]:
    """Parse semicolon-separated keywords into a list."""
    if not val or not val.strip():
        return []
    return [kw.strip() for kw in val.split(";") if kw.strip()]


def _parse_context_array(val: str) -> list[str]:
    """Parse semicolon/comma-separated context value. 'ALL' → empty list (means all)."""
    val = val.strip()
    if not val or val.upper() in ("ALL", "WSZYSTKIE", "WSZYSTKO"):
        return []
    return [v.strip() for v in re.split(r"[;,]", val) if v.strip()]


def _map_data_type(sheet_type: str) -> str:
    """Map Sheet data_type to DB feature_type."""
    mapping = {
        "bool": "boolean",
        "boolean": "boolean",
        "int": "numeric",
        "float": "numeric",
        "numeric": "numeric",
        "enum": "enum",
        "text": "text",
    }
    return mapping.get(sheet_type.strip().lower(), "text")


# ---------------------------------------------------------------------------
# IMPORT: Sheet → DB
# ---------------------------------------------------------------------------


def import_from_sheet() -> dict[str, int]:
    """Read Google Sheet 'cechy' and upsert into universal_features.

    Returns counts: {added, updated, skipped, errors}.
    """
    gc = _get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = ss.worksheet(SHEET_NAME)

    data = ws.get_all_values()
    if len(data) < 2:
        logger.warning("Sheet '%s' is empty or has no data rows", SHEET_NAME)
        return {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    headers = [h.strip() for h in data[0]]
    rows = data[1:]

    logger.info(
        "Sheet '%s': %d headers, %d data rows",
        SHEET_NAME,
        len(headers),
        len(rows),
    )

    # Build column index map
    col_indices: dict[str, int] = {}
    for idx, h in enumerate(headers):
        if h in SHEET_TO_DB:
            col_indices[h] = idx

    if "Technical_Key" not in col_indices:
        msg = f"Missing required column 'Technical_Key'. Found headers: {headers}"
        raise ValueError(msg)

    # Load existing features for matching
    existing_result = (
        supabase.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key, display_name")
        .execute()
    )
    existing_by_feature_key: dict[str, dict] = {}
    existing_by_display: dict[str, dict] = {}
    for feat in existing_result.data:
        if feat.get("feature_key"):
            existing_by_feature_key[feat["feature_key"]] = feat
        if feat.get("display_name"):
            existing_by_display[feat["display_name"]] = feat

    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    for row_idx, row in enumerate(rows, start=2):
        try:
            tech_key_idx = col_indices["Technical_Key"]
            feature_key = row[tech_key_idx].strip() if len(row) > tech_key_idx else ""

            if not feature_key:
                stats["skipped"] += 1
                continue

            # Build update payload
            payload: dict[str, object] = {}

            for sheet_col, db_col in SHEET_TO_DB.items():
                if sheet_col == "Technical_Key":
                    continue  # handled separately as the primary key
                if sheet_col not in col_indices:
                    continue
                idx = col_indices[sheet_col]
                if idx >= len(row):
                    continue
                raw = row[idx].strip()
                if not raw:
                    continue

                # Type-specific parsing
                if db_col in ("is_derived", "is_contextual", "is_filterable"):
                    payload[db_col] = _parse_bool(raw)
                elif db_col == "trigger_keywords":
                    payload[db_col] = _parse_keywords(raw)
                elif db_col in (
                    "applies_to_vehicle_categories",
                    "applies_to_body_subtypes",
                    "applies_to_powertrains",
                    "applies_to_drivetrains",
                ):
                    payload[db_col] = _parse_context_array(raw)
                elif db_col == "feature_type":
                    payload[db_col] = _map_data_type(raw)
                else:
                    payload[db_col] = raw

            # Upsert logic
            feature_id = None
            existing = existing_by_feature_key.get(feature_key)
            if existing:
                feature_id = existing["id"]
                # UPDATE existing feature (do not touch feature_key)
                if payload:
                    (
                        supabase.schema("reverse_search")
                        .table("universal_features")
                        .update(payload)
                        .eq("id", feature_id)
                        .execute()
                    )
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                # Try matching by display_name
                display_name = payload.get("display_name", "")
                match = (
                    existing_by_display.get(str(display_name)) if display_name else None
                )

                if match:
                    feature_id = match["id"]
                    payload["feature_key"] = feature_key
                    (
                        supabase.schema("reverse_search")
                        .table("universal_features")
                        .update(payload)
                        .eq("id", feature_id)
                        .execute()
                    )
                    stats["updated"] += 1
                else:
                    # INSERT new feature
                    if "display_name" not in payload:
                        payload["display_name"] = feature_key
                    payload["feature_key"] = feature_key
                    payload["is_active"] = True

                    inserted = (
                        supabase.schema("reverse_search")
                        .table("universal_features")
                        .insert(payload)
                        .execute()
                    )
                    if inserted.data:
                        feature_id = inserted.data[0]["id"]
                    stats["added"] += 1

        except Exception:
            logger.exception("Error processing row %d", row_idx)
            stats["errors"] += 1

    logger.info("Import complete: %s", stats)

    # Hygiene check: detect "both filterable" duplicate pairs (naked + eq_/spec_/dim_).
    try:
        all_resp = (
            supabase.schema("reverse_search")
            .table("universal_features")
            .select("feature_key, display_name, is_filterable")
            .eq("is_active", True)
            .eq("is_filterable", True)
            .execute()
        )
        keys = {r["feature_key"] for r in all_resp.data or []}
        leaks: list[tuple[str, str]] = []
        for k in keys:
            for prefix in ("eq_", "spec_", "dim_"):
                if not k.startswith(prefix):
                    if (prefix + k) in keys:
                        leaks.append((k, prefix + k))
        if leaks:
            logger.warning(
                "MDM HYGIENE: %d duplicate filterable pair(s) detected. Mark naked variant as Is_Filterable=FALSE in gsheet. Pairs: %s",
                len(leaks),
                leaks[:10],
            )
    except Exception as exc:
        logger.debug("Hygiene check failed: %s", exc)

    if stats.get("added") or stats.get("updated"):
        try:
            from core.feature_catalog_loader import invalidate_catalog_cache

            n = invalidate_catalog_cache()
            logger.info("Reverse Search catalog cache invalidated (%d keys)", n)
        except Exception as exc:
            logger.warning("Failed to invalidate catalog cache: %s", exc)

    return stats


# ---------------------------------------------------------------------------
# EXPORT: DB → Sheet (backfill)
# ---------------------------------------------------------------------------


def export_to_sheet() -> int:
    """Export all universal_features to the Google Sheet 'cechy'.

    Creates headers if Sheet is empty, then dumps all features.
    Returns count of rows written.
    """
    gc = _get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)

    try:
        ws = ss.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = ss.add_worksheet(SHEET_NAME, rows=300, cols=20)
        logger.info("Created new worksheet '%s'", SHEET_NAME)

    # Fetch all features from DB
    result = (
        supabase.schema("reverse_search")
        .table("universal_features")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )

    features = result.data
    if not features:
        logger.warning("No features found in DB to export")
        return 0

    # Export headers and their DB column names
    export_headers = [
        "Technical_Key",
        "Functional_Name",
        "Category",
        "Data_Type",
        "Unit_Source",
        "Unit_Target",
        "Transformation",
        "Trigger_Keywords",
        "Kategoria_Pojazdu",
        "Body_Context",
        "Powertrain_Context",
        "Drivetrain_Context",
        "Is_Filterable",
        "Is_Derived",
        "Is_Contextual",
    ]

    db_col_map: dict[str, str] = {
        "Technical_Key": "feature_key",
        "Functional_Name": "display_name",
        "Category": "category",
        "Data_Type": "feature_type",
        "Unit_Source": "unit_source",
        "Unit_Target": "unit_target",
        "Transformation": "transformation",
        "Trigger_Keywords": "trigger_keywords",
        "Kategoria_Pojazdu": "applies_to_vehicle_categories",
        "Body_Context": "applies_to_body_subtypes",
        "Powertrain_Context": "applies_to_powertrains",
        "Drivetrain_Context": "applies_to_drivetrains",
        "Is_Filterable": "is_filterable",
        "Is_Derived": "is_derived",
        "Is_Contextual": "is_contextual",
    }

    rows_to_write = [export_headers]

    for feat in features:
        row: list[str] = []
        for header in export_headers:
            db_col = db_col_map.get(header, "")
            value = feat.get(db_col, "")

            if value is None:
                value = ""
            elif isinstance(value, bool):
                value = "TRUE" if value else "FALSE"
            elif isinstance(value, list):
                if not value:
                    value = "ALL"
                else:
                    value = "; ".join(str(v) for v in value)
            else:
                value = str(value)

            row.append(value)

        rows_to_write.append(row)

    # Write all at once (efficient batch update)
    ws.clear()
    n_cols = len(export_headers)
    col_letter = chr(ord("A") + n_cols - 1)
    ws.update(
        range_name=f"A1:{col_letter}{len(rows_to_write)}",
        values=rows_to_write,
    )

    logger.info(
        "Exported %d features to sheet '%s'",
        len(features),
        SHEET_NAME,
    )
    return len(features)


# ---------------------------------------------------------------------------
# DICTIONARIES: simple `id, name` lookup tables
# ---------------------------------------------------------------------------

# Shape: gsheet tab → (DB table, header → column).
# Each tab is a 2-column dictionary (ID + label) seeded into a public table
# that the frontend reads directly via supabase-js. Idempotent upsert by id.
DICT_SYNCS: dict[str, tuple[str, dict[str, str]]] = {
    "transmission_dict": (
        "transmission_types",
        {"ID": "id", "Nazwa Skrzyni": "name"},
    ),
}


def import_dictionary(sheet_name: str) -> dict[str, int]:
    """Read a 2-column dictionary tab and upsert into its public table."""
    if sheet_name not in DICT_SYNCS:
        raise ValueError(f"Unknown dictionary sheet '{sheet_name}'. Known: {list(DICT_SYNCS)}")

    table_name, header_map = DICT_SYNCS[sheet_name]

    gc = _get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = ss.worksheet(sheet_name)
    data = ws.get_all_values()

    if len(data) < 2:
        logger.warning("Sheet '%s' is empty or has no data rows", sheet_name)
        return {"upserted": 0, "skipped": 0, "errors": 0}

    headers = [h.strip() for h in data[0]]
    col_idx = {h: i for i, h in enumerate(headers) if h in header_map}
    missing = [h for h in header_map if h not in col_idx]
    if missing:
        msg = f"Sheet '{sheet_name}' missing required columns: {missing}. Found: {headers}"
        raise ValueError(msg)

    rows = []
    stats = {"upserted": 0, "skipped": 0, "errors": 0}
    for row in data[1:]:
        try:
            payload: dict[str, object] = {}
            for sheet_col, db_col in header_map.items():
                idx = col_idx[sheet_col]
                if idx >= len(row):
                    continue
                raw = row[idx].strip()
                if not raw:
                    continue
                payload[db_col] = int(raw) if db_col == "id" else raw
            if "id" not in payload or "name" not in payload:
                stats["skipped"] += 1
                continue
            rows.append(payload)
        except Exception:
            logger.exception("Error parsing row in sheet '%s'", sheet_name)
            stats["errors"] += 1

    if rows:
        supabase.table(table_name).upsert(rows, on_conflict="id").execute()
        stats["upserted"] = len(rows)

    logger.info("Dictionary sync '%s' → %s: %s", sheet_name, table_name, stats)
    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "export":
        count = export_to_sheet()
        print(f"Exported {count} features to Sheet")
    elif len(sys.argv) > 1 and sys.argv[1] == "import":
        stats = import_from_sheet()
        print(f"Import results: {stats}")
    elif len(sys.argv) > 2 and sys.argv[1] == "import-dict":
        stats = import_dictionary(sys.argv[2])
        print(f"Dictionary import results: {stats}")
    else:
        print("Usage: python mdm_sync.py [export|import|import-dict <sheet_name>]")
        print("  export                       - DB → Google Sheet (backfill all features)")
        print("  import                       - Google Sheet 'cechy' → DB universal_features")
        print(f"  import-dict <sheet_name>     - Dictionary tab → DB. Available: {list(DICT_SYNCS)}")
