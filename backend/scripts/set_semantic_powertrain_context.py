"""Ustawia semantycznie poprawne wartości Powertrain_Context dla cech specyficznych.

Skrypt idempotentny — bezpieczny do wielokrotnego uruchomienia.
Uruchom po każdym eksporcie z DB jeśli dane zostaną nadpisane.

Strategia:
- Cechy LPG     → 'LPG'
- Cechy BEV     → 'Elektryczny (BEV)'
- Reszta        → 'ALL' (brak zmiany)

Wartości muszą istnieć dokładnie w REF_SILNIKI kolumna B (słownik nadrzędny).
"""

from __future__ import annotations

import logging
import os
import sys

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = os.environ.get(
    "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
)

COL_TECH_KEY = 0
COL_POWERTRAIN = 11  # Kolumna L (0-indexed)

# ---------------------------------------------------------------------------
# Mapowanie: technical_key → wartość w REF_SILNIKI!$B (Powertrain_Context)
# ---------------------------------------------------------------------------
SEMANTIC_POWERTRAIN: dict[str, str] = {
    # --- LPG ---
    "instalacja_lpg_taknie": "LPG",
    "marka_instalacji_lpg": "LPG",
    "model_instalacji_lpg": "LPG",
    "gwarantinstalator_instalacji_lpg": "LPG",
    "cykl_obowiązkowego_serwisu_instalacji_lpg_w_kmmiesiącach": "LPG",
    "producent_zbiornika_lpg": "LPG",
    "pojemność_zbiornika_lpg_w_litrach": "LPG",
    "nr_fabryczny_zbiornika_lpg": "LPG",
    # --- Elektryczne (BEV) ---
    "zasięg_wltp_dla_pojazdów_elektrycznych_w_km": "Elektryczny (BEV)",
    "pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh": "Elektryczny (BEV)",
    "funkcja_szybkiego_ładowania_samochodu": "Elektryczny (BEV)",
}


def apply_semantic_powertrain() -> int:
    """Ustawia wartości Powertrain_Context. Zwraca liczbę zaktualizowanych wierszy."""
    key_path = SA_KEY_PATH
    creds = Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = ss.worksheet("cechy")

    all_rows = ws.get_all_values()
    cells: list[gspread.Cell] = []

    for row_idx, row in enumerate(all_rows):
        if row_idx == 0:
            continue
        tech_key = row[COL_TECH_KEY].strip() if row else ""
        if tech_key not in SEMANTIC_POWERTRAIN:
            continue
        desired = SEMANTIC_POWERTRAIN[tech_key]
        current = row[COL_POWERTRAIN].strip() if len(row) > COL_POWERTRAIN else ""
        if current != desired:
            logger.info("  %s: '%s' → '%s'", tech_key, current, desired)
            cells.append(
                gspread.Cell(row=row_idx + 1, col=COL_POWERTRAIN + 1, value=desired)
            )

    if cells:
        ws.update_cells(cells, value_input_option="RAW")
        logger.info("Zaktualizowano %d komórek.", len(cells))
    else:
        logger.info("Brak zmian — wszystko aktualne.")

    return len(cells)


if __name__ == "__main__":
    count = apply_semantic_powertrain()
    print(f"Zaktualizowano {count} komórek Powertrain_Context.")
