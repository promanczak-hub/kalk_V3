"""
Sync service multipliers from Google Sheets 'cechy' (service_rates_config) to Supabase tables using SQL generation for execution in MCP.
"""

from __future__ import annotations

import logging
import sys

from scripts.mdm_sync import _get_gspread_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SHEET_NAME = "service_rates_config"


def main() -> None:
    gc = _get_gspread_client()
    try:
        ss = gc.open_by_key(SPREADSHEET_ID)
        ws = ss.worksheet(SHEET_NAME)
    except Exception as e:
        logger.error(f"Cannot open worksheet: {e}")
        sys.exit(1)

    data = ws.get_all_values()
    if not data or len(data) < 2:
        logger.error("Sheet is empty or missing data.")
        sys.exit(1)

    sql_lines = []

    # Process BRAND multipliers (cols 0, 1)
    brands = []
    for row in data[1:]:
        if (
            len(row) > 1
            and row[0].strip()
            and row[1].strip()
            and row[1].replace(",", ".").replace(".", "", 1).isdigit()
        ):
            val = float(row[1].replace(",", "."))
            brands.append((row[0].strip().upper(), val))

    if brands:
        sql_lines.append("TRUNCATE TABLE samar_service_brand_multipliers;")
        for b, v in brands:
            sql_lines.append(
                f"INSERT INTO samar_service_brand_multipliers (brand_normalized, multiplier) VALUES ('{b.replace(chr(39), chr(39) + chr(39))}', {v});"
            )

    # Process DRIVETRAIN multipliers (cols 3, 4) -> Mnożniki NAPĘD
    drives = []
    for row in data[1:]:
        if (
            len(row) > 4
            and row[3].strip()
            and row[4].strip()
            and row[4].replace(",", ".").replace(".", "", 1).isdigit()
        ):
            val = float(row[4].replace(",", "."))
            drives.append((row[3].strip().upper(), val))

    if drives:
        sql_lines.append("TRUNCATE TABLE samar_service_drive_multipliers;")
        for d, v in drives:
            sql_lines.append(
                f"INSERT INTO samar_service_drive_multipliers (drive_normalized, multiplier) VALUES ('{d.replace(chr(39), chr(39) + chr(39))}', {v});"
            )

    # Process FUEL multipliers (cols 6, 7) -> Mnożniki PALIWO
    fuels = []
    for row in data[1:]:
        if (
            len(row) > 7
            and row[6].strip()
            and row[7].strip()
            and row[7].replace(",", ".").replace(".", "", 1).isdigit()
        ):
            val = float(row[7].replace(",", "."))
            fuels.append((row[6].strip().upper(), val))

    if fuels:
        sql_lines.append("TRUNCATE TABLE samar_service_fuel_multipliers;")
        for f, v in fuels:
            sql_lines.append(
                f"INSERT INTO samar_service_fuel_multipliers (fuel_normalized, multiplier) VALUES ('{f.replace(chr(39), chr(39) + chr(39))}', {v});"
            )

    # Process GEARBOX multipliers (cols 9, 10) -> Mnożniki SKRZYNIA
    gearboxes = []
    for row in data[1:]:
        if (
            len(row) > 10
            and row[9].strip()
            and row[10].strip()
            and row[10].replace(",", ".").replace(".", "", 1).isdigit()
        ):
            val = float(row[10].replace(",", "."))
            gearboxes.append((row[9].strip().upper(), val))

    if gearboxes:
        sql_lines.append("TRUNCATE TABLE samar_service_gearbox_multipliers;")
        for g, v in gearboxes:
            sql_lines.append(
                f"INSERT INTO samar_service_gearbox_multipliers (gearbox_normalized, multiplier) VALUES ('{g.replace(chr(39), chr(39) + chr(39))}', {v});"
            )

    with open(
        "D:/kalk_v3/backend/scripts/sync_service_multipliers.sql", "w", encoding="utf-8"
    ) as f:
        f.write("\n".join(sql_lines))

    logger.info(
        "SQL generated: D:/kalk_v3/backend/scripts/sync_service_multipliers.sql"
    )


if __name__ == "__main__":
    main()
