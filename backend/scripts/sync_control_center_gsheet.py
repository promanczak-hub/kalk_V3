"""Sync control_center singleton from Google Sheet 'Globalne ustawienia'.

One-way: sheet -> public.control_center (id=1).

Reads the same tab as sync_tyre_config_v3.py (gid 890315543) which is structured
as key/value pairs (column index 3 = db_key, column index 1 = value). Only the
keys that map to columns in `public.control_center` are upserted; tyre-related
keys are ignored (they continue to be handled by sync_tyre_config_v3.py).

Run from the backend root:
    poetry run python scripts/sync_control_center_gsheet.py
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from core.database import supabase

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("sync_control_center")

load_dotenv()

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
GLOBAL_SETTINGS_GID = 890315543

# Mapping: sheet db_key -> (control_center column, type cast)
# Only keys that exist in public.control_center are listed. Other keys in the
# tab (tyre thresholds, cost_tyre_*) are handled by sync_tyre_config_v3.py.
CONTROL_CENTER_FIELDS: dict[str, type] = {
    "default_wibor": float,
    "default_ltr_margin": float,
    "vat_rate": float,
    "bank_spread": float,
    "resale_time_days": int,
    "ins_avg_damage_value": float,
    "ins_avg_damage_mileage": int,
    "cost_gsm_subscription_monthly": float,
    "cost_gsm_device": float,
    "cost_gsm_installation": float,
    "gsm_amortization_years": float,
    "cost_hook_installation": float,
    "cost_grid_dismantling": float,
    "cost_registration": float,
    "cost_sales_prep": float,
    "cost_transport": float,
    "normatywny_przebieg_mc": int,
    "przewidywana_cena_sprzedazy_lo": float,
    "budzet_marketingowy_ltr": float,
}


def get_gspread_client() -> gspread.Client:
    key_path = os.environ.get(
        "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
    )
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)


def _coerce(raw: str, cast: type) -> int | float | None:
    raw = raw.strip().replace(",", ".")
    if not raw:
        return None
    try:
        if cast is int:
            return int(float(raw))
        return float(raw)
    except ValueError:
        return None


def main() -> None:
    log.info("Reading 'Globalne ustawienia' (gid=%d)...", GLOBAL_SETTINGS_GID)
    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = next((w for w in ss.worksheets() if w.id == GLOBAL_SETTINGS_GID), None)
    if not ws:
        log.error("Worksheet with gid=%d not found", GLOBAL_SETTINGS_GID)
        raise SystemExit(1)

    rows = ws.get_all_values()
    if len(rows) < 2:
        log.error("Sheet '%s' is empty", ws.title)
        raise SystemExit(1)

    # Same column convention as sync_tyre_config_v3.py:
    #   col index 3 = db_key, col index 1 = value
    payload: dict[str, int | float] = {}
    skipped: list[str] = []
    for row in rows[1:]:
        if len(row) < 4:
            continue
        db_key = row[3].strip()
        if not db_key:
            continue
        if db_key not in CONTROL_CENTER_FIELDS:
            skipped.append(db_key)
            continue
        value = _coerce(row[1], CONTROL_CENTER_FIELDS[db_key])
        if value is None:
            log.warning("  %s: empty/non-numeric value, skipping", db_key)
            continue
        payload[db_key] = value

    log.info(
        "Mapped %d/%d control_center fields from sheet (skipped non-cc keys: %s)",
        len(payload),
        len(CONTROL_CENTER_FIELDS),
        ", ".join(sorted(set(skipped))) or "none",
    )

    missing = [k for k in CONTROL_CENTER_FIELDS if k not in payload]
    if missing:
        log.warning("Fields not present in sheet (DB keeps current value): %s", missing)

    if not payload:
        log.error("No control_center fields found in sheet — nothing to update.")
        raise SystemExit(1)

    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    log.info("Updating public.control_center where id=1 with %d fields...", len(payload) - 1)
    res = supabase.table("control_center").update(payload).eq("id", 1).execute()
    if not res.data:
        log.error("Update returned no rows — singleton row may be missing.")
        raise SystemExit(1)

    log.info("OK. Updated columns: %s", sorted(k for k in payload if k != "updated_at"))


if __name__ == "__main__":
    main()
