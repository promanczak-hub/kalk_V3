"""Sync control_center (EAV key/value) from Google Sheet 'Globalne ustawienia'.

One-way: sheet -> public.control_center (pionowa tabela key/value).

Tab 'Globalne ustawienia' (gid 890315543) jest key/value (col index 3 =
db_key, col index 1 = value). Kazdy klucz z CONTROL_CENTER_FIELDS trafia
jako wiersz do tabeli control_center (upsert po `key`).

Run from the backend root:
    poetry run python scripts/sync_control_center_gsheet.py
"""

from __future__ import annotations

import logging
import os

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from core.control_center import update_control_center_fields

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("sync_control_center")

load_dotenv()

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
GLOBAL_SETTINGS_GID = 890315543

# Mapping: sheet db_key -> (control_center column, type cast).
# Wszystkie globalne parametry aplikacji LTR (finanse, koszty operacyjne,
# opony, ubezpieczenia, sprzedaz) trzymane sa jako kolumny w singletonie
# control_center (id=1).
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
    # Opony (przeniesione z global_setup 2026-05-16)
    "cost_tyre_storage": float,
    "cost_tyre_swap": float,
    "all_season_threshold_1": float,
    "all_season_threshold_2": float,
    "all_season_threshold_3": float,
    "all_season_threshold_4": float,
    "all_season_threshold_5": float,
    "season_threshold_1": float,
    "season_threshold_2": float,
    "season_threshold_3": float,
    "season_threshold_4": float,
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

    # Konwencja kolumn arkusza: col index 3 = db_key, col index 1 = value.
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

    log.info("Upserting %d key/value rows into public.control_center...", len(payload))
    written = update_control_center_fields(payload)
    if not written:
        log.error("Upsert returned no rows — check RLS / connectivity.")
        raise SystemExit(1)

    log.info("OK. Upserted keys: %s", sorted(payload.keys()))


if __name__ == "__main__":
    main()
