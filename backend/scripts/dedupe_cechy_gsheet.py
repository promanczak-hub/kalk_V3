"""One-shot script: mark 13 naked-duplicate equipment features as
Is_Filterable=FALSE in the gsheet `cechy` tab.

This must be run once after the matching DB migration
(20260428220000_deactivate_naked_duplicates_of_eq_features) so that the next
`mdm_sync.import_from_sheet()` does NOT revert is_filterable back to TRUE.

Idempotent: skips rows that are already FALSE.
"""

from __future__ import annotations

import logging
import os
import sys

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SA_KEY_PATH = os.environ.get(
    "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
)
SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SHEET_NAME = "cechy"

DEPRECATED_NAKED_KEYS: set[str] = {
    "abs",
    "aktywny_tempomat",
    "apple_car_play",
    "asr",
    "asystent_zmiany_pasa_ruchu",
    "czujniki_parkowania_tyl",
    "ekran_dotykowy",
    "esp",
    "felga_aluminiowa",
    "funkcja_szybkiego_ladowania_samochodu",
    "gps_nawigacja_satelitarna",
    "klimatyzacja_automatyczna",
    "klimatyzacja_dla_pasazerow_z_tylu",
}


def _ascii_normalize(s: str) -> str:
    """Strip Polish diacritics so 'czujniki_parkowania_tył' matches 'czujniki_parkowania_tyl'."""
    table = str.maketrans(
        "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
        "acelnoszzACELNOSZZ",
    )
    return s.translate(table).strip().lower()


_DEPRECATED_NORMALIZED = {_ascii_normalize(k) for k in DEPRECATED_NAKED_KEYS}


def main() -> int:
    creds = Credentials.from_service_account_file(
        SA_KEY_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

    rows = ws.get_all_values()
    if not rows:
        logger.error("Sheet is empty.")
        return 1

    headers = [h.strip() for h in rows[0]]

    # Locate technical_key column. Real header is sometimes "Technical_Key", sometimes "f"
    # (legacy truncation), sometimes column 1 by convention.
    tk_idx: int | None = None
    for candidate in ("Technical_Key", "technical_key", "f"):
        if candidate in headers:
            tk_idx = headers.index(candidate)
            break
    if tk_idx is None:
        tk_idx = 0  # fallback: assume column 1
        logger.warning(
            "Technical_Key column header not recognized; assuming column 1. Headers: %s",
            headers,
        )

    if "Is_Filterable" not in headers:
        logger.error("Missing 'Is_Filterable' column. Found: %s", headers)
        return 1
    if_idx = headers.index("Is_Filterable")
    logger.info(
        "Using technical_key column at index %d (header=%r), is_filterable at index %d.",
        tk_idx, headers[tk_idx], if_idx,
    )

    updates: list[dict[str, object]] = []
    already_false = 0
    not_found = set(_DEPRECATED_NORMALIZED)

    for row_num, row in enumerate(rows[1:], start=2):
        if len(row) <= tk_idx:
            continue
        tk_raw = row[tk_idx].strip()
        tk_norm = _ascii_normalize(tk_raw)
        if tk_norm not in _DEPRECATED_NORMALIZED:
            continue
        not_found.discard(tk_norm)
        tk = tk_raw  # keep original for logging

        current = row[if_idx].strip().upper() if len(row) > if_idx else ""
        if current == "FALSE":
            already_false += 1
            logger.info("OK (already FALSE): row %d %s", row_num, tk)
            continue

        cell = rowcol_to_a1(row_num, if_idx + 1)
        updates.append({"range": cell, "values": [["FALSE"]]})
        logger.info("Will mark row %d (%s) at %s = FALSE", row_num, tk, cell)

    if not_found:
        logger.warning(
            "These technical_keys were not found in sheet (already removed?): %s",
            sorted(not_found),
        )

    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        logger.info(
            "Updated %d rows. (Already-FALSE: %d. Not found: %d.)",
            len(updates),
            already_false,
            len(not_found),
        )
    else:
        logger.info(
            "Nothing to update. (Already-FALSE: %d. Not found: %d.)",
            already_false,
            len(not_found),
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
