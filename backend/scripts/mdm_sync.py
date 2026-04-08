"""MDM Sync: Google Sheet 'cechy' ↔ Supabase universal_features.

Bidirectional sync:
1. EXPORT: Dumps all 191 DB features → Sheet (backfill)
2. IMPORT: Reads Sheet → upserts into DB (ongoing sync)

Uses technical_key as the primary sync identity.
Never deletes — only ADD / UPDATE.
"""

from __future__ import annotations

import logging
import os

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
    "Technical_Key": "technical_key",
    "Functional_Name": "display_name",
    "Data_Type": "feature_type",
    "Unit_Source": "unit_source",
    "Unit_Target": "unit_target",
    "Transformation": "transformation_rule",
    "Trigger_Keywords": "trigger_keywords",
    "Visibility_Group": "body_context",
    "Feature_Tier": "feature_tier",
    "Kategoria_Pojazdu": "vehicle_category",
    "Body_Context": "body_context",
    "Powertrain_Context": "powertrain_context",
    "Drivetrain_Context": "drivetrain_context",
    "Is_Tender_Criteria": "is_tender_criteria",
    "Required_For_Tender": "required_for_tender",
    "Is_Derived": "is_derived",
    "Is_Contextual": "is_contextual",
    "Is_Mandatory_For_Matching": "is_mandatory_for_matching",
    "Is_Comparable": "is_comparable",
    "Data_Confidence_Required": "data_confidence_required",
    "Is_Filterable": "is_filterable",
    "Category": "category_name",
    "Fallback_Source": "fallback_source",
}

# DB column → Sheet header (reverse for export)
DB_TO_SHEET: dict[str, str] = {v: k for k, v in SHEET_TO_DB.items()}


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


def _map_vehicle_category(val: str) -> str:
    """Map Polish Kategoria_Pojazdu to DB vehicle_category enum."""
    val = val.strip().lower()
    if val in ("osobowe", "passenger"):
        return "PASSENGER"
    elif val in ("ciężarowe", "dostawcze", "commercial"):
        return "COMMERCIAL"
    return "ALL"


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

    import re

    # Load body types for M2M Fail-Fast logic
    body_types_result = (
        supabase.table("body_types").select("id, nazwa_nadwozia, typ_pojazdu").execute()
    )
    body_types_dict: dict[str, dict] = {
        bt["nazwa_nadwozia"].strip().upper(): bt for bt in body_types_result.data
    }

    # Load existing features for matching
    existing_result = (
        supabase.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key, technical_key, display_name")
        .execute()
    )
    existing_by_tech_key: dict[str, dict] = {}
    existing_by_display: dict[str, dict] = {}
    for feat in existing_result.data:
        if feat.get("technical_key"):
            existing_by_tech_key[feat["technical_key"]] = feat
        if feat.get("display_name"):
            existing_by_display[feat["display_name"]] = feat

    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    for row_idx, row in enumerate(rows, start=2):
        try:
            tech_key_idx = col_indices["Technical_Key"]
            tech_key = row[tech_key_idx].strip() if len(row) > tech_key_idx else ""

            if not tech_key:
                stats["skipped"] += 1
                continue

            # Build update payload
            payload: dict[str, object] = {"technical_key": tech_key}

            for sheet_col, db_col in SHEET_TO_DB.items():
                if sheet_col not in col_indices:
                    continue
                idx = col_indices[sheet_col]
                if idx >= len(row):
                    continue
                raw = row[idx].strip()
                if not raw:
                    continue

                # Type-specific parsing
                if db_col in (
                    "is_tender_criteria",
                    "required_for_tender",
                    "is_derived",
                    "is_contextual",
                    "is_mandatory_for_matching",
                    "is_comparable",
                    "data_confidence_required",
                    "is_filterable",
                ):
                    payload[db_col] = _parse_bool(raw)
                elif db_col == "trigger_keywords":
                    payload[db_col] = _parse_keywords(raw)
                elif db_col == "feature_type":
                    payload[db_col] = _map_data_type(raw)
                elif db_col == "feature_tier":
                    tier = raw.strip().upper()
                    if tier in ("CORE", "EXTENDED", "EDGE"):
                        payload[db_col] = tier
                elif db_col == "vehicle_category":
                    payload[db_col] = _map_vehicle_category(raw)
                else:
                    payload[db_col] = raw

            # Upsert logic
            feature_id = None
            existing = existing_by_tech_key.get(tech_key)
            if existing:
                feature_id = existing["id"]
                # UPDATE existing feature
                payload.pop("technical_key", None)
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
                    # UPDATE existing + set technical_key
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
                        payload["display_name"] = tech_key
                    payload["feature_key"] = tech_key
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

            # Build M2M body relations using Fail-Fast
            if feature_id and "Body_Context" in col_indices:
                raw_body = row[col_indices["Body_Context"]].strip()
                # Clear any existing relations (cleanup)
                supabase.schema("reverse_search").table(
                    "feature_body_applicability"
                ).delete().eq("feature_id", feature_id).execute()

                veh_cat = payload.get("vehicle_category", "ALL")
                universe_ids = set()
                for uname, udata in body_types_dict.items():
                    if veh_cat == "PASSENGER" and udata.get("typ_pojazdu") != "Osobowy":
                        continue
                    if (
                        veh_cat == "COMMERCIAL"
                        and udata.get("typ_pojazdu") != "Ciężarowy"
                    ):
                        continue
                    universe_ids.add(udata["id"])

                if not raw_body or raw_body.upper() in ("ALL", "WSZYSTKIE", "WSZYSTKO"):
                    body_ids = universe_ids
                else:
                    parts = [
                        p.strip() for p in re.split(r"[/,]", raw_body) if p.strip()
                    ]
                    body_ids = set()

                    # If all parts are exclusions, start with universe
                    if all(p.startswith(("!", "-")) for p in parts):
                        body_ids = set(universe_ids)

                    for p in parts:
                        is_exclusion = p.startswith(("!", "-"))
                        p_clean = p[1:].strip().upper() if is_exclusion else p.upper()

                        if p_clean not in body_types_dict:
                            raise ValueError(
                                f"Nieznany typ nadwozia: '{p_clean}' w CESZE '{tech_key}'. Weryfikacja Fail-Fast odrzucona!"
                            )

                        bt_data = body_types_dict[p_clean]
                        bt_id = bt_data["id"]

                        # Cross-validation
                        if (
                            veh_cat == "PASSENGER"
                            and bt_data.get("typ_pojazdu") != "Osobowy"
                        ):
                            raise ValueError(
                                f"Niezgodność: Cecha '{tech_key}' ma kategorię Osobowe, ale typ nadwozia '{p_clean}' to Ciężarowy. Weryfikacja Fail-Fast odrzucona!"
                            )
                        if (
                            veh_cat == "COMMERCIAL"
                            and bt_data.get("typ_pojazdu") != "Ciężarowy"
                        ):
                            raise ValueError(
                                f"Niezgodność: Cecha '{tech_key}' ma kategorię Ciężarowe, ale typ nadwozia '{p_clean}' to Osobowy. Weryfikacja Fail-Fast odrzucona!"
                            )

                        if is_exclusion:
                            body_ids.discard(bt_id)
                        else:
                            body_ids.add(bt_id)

                # Update relations
                if body_ids:
                    m2m_payload = [
                        {"feature_id": feature_id, "body_type_id": bid}
                        for bid in set(body_ids)
                    ]
                    supabase.schema("reverse_search").table(
                        "feature_body_applicability"
                    ).insert(m2m_payload).execute()

        except Exception:
            logger.exception("Error processing row %d", row_idx)
            stats["errors"] += 1

    logger.info("Import complete: %s", stats)
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

    # Define export headers
    export_headers = [
        "Technical_Key",
        "Functional_Name",
        "Category",
        "Data_Type",
        "Unit_Source",
        "Unit_Target",
        "Transformation",
        "Trigger_Keywords",
        "Feature_Tier",
        "Kategoria_Pojazdu",
        "Body_Context",
        "Powertrain_Context",
        "Drivetrain_Context",
        "Is_Filterable",
        "Is_Tender_Criteria",
        "Required_For_Tender",
        "Is_Derived",
        "Is_Contextual",
        "Is_Mandatory_For_Matching",
        "Is_Comparable",
        "Data_Confidence_Required",
        "Fallback_Source",
    ]

    # Map DB columns to export values
    db_col_map: dict[str, str] = {
        "Technical_Key": "technical_key",
        "Functional_Name": "display_name",
        "Category": "category_name",
        "Data_Type": "feature_type",
        "Unit_Source": "unit_source",
        "Unit_Target": "unit_target",
        "Transformation": "transformation_rule",
        "Trigger_Keywords": "trigger_keywords",
        "Feature_Tier": "feature_tier",
        "Kategoria_Pojazdu": "vehicle_category",
        "Body_Context": "body_context",
        "Powertrain_Context": "powertrain_context",
        "Drivetrain_Context": "drivetrain_context",
        "Is_Filterable": "is_filterable",
        "Is_Tender_Criteria": "is_tender_criteria",
        "Required_For_Tender": "required_for_tender",
        "Is_Derived": "is_derived",
        "Is_Contextual": "is_contextual",
        "Is_Mandatory_For_Matching": "is_mandatory_for_matching",
        "Is_Comparable": "is_comparable",
        "Data_Confidence_Required": "data_confidence_required",
        "Fallback_Source": "fallback_source",
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
                value = "; ".join(str(v) for v in value)
            else:
                value = str(value)

            # Polonize Vehicle Category for Business Output
            if header == "Kategoria_Pojazdu":
                if value == "PASSENGER":
                    value = "Osobowe"
                elif value == "COMMERCIAL":
                    value = "Ciężarowe"
                else:
                    value = "Wszystkie"

            # Use feature_key as fallback for technical_key
            if header == "Technical_Key" and not value:
                value = feat.get("feature_key", "")

            row.append(value)

        rows_to_write.append(row)

    # Write all at once (efficient batch update)
    ws.clear()
    ws.update(
        range_name=f"A1:S{len(rows_to_write)}",
        values=rows_to_write,
    )

    logger.info(
        "Exported %d features to sheet '%s'",
        len(features),
        SHEET_NAME,
    )
    return len(features)


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
    else:
        print("Usage: python mdm_sync.py [export|import]")
        print("  export - DB → Google Sheet (backfill all 191 features)")
        print("  import - Google Sheet → DB (sync MDM changes)")
