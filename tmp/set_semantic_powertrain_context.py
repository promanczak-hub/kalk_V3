"""Ustawia semantycznie poprawne wartości Powertrain_Context dla cech specyficznych.

Strategia:
- Cechy LPG          → 'LPG'
- Cechy BEV/EV       → 'Elektryczny (BEV)'
- Cechy PHEV         → 'Plug-in Hybrid (PHEV)'
- Cechy HEV          → 'Hybryda (HEV)'
- Cechy ICE          → zależy od kontekstu (benzyna/diesel/ALL)
- Reszta             → 'ALL' (brak zmiany)

Uwaga: Google Sheets dropdown = single-select, więc dla cech multi-type
wybieramy wartość DOMINUJĄCĄ/PIERWSZĄ z oryginalnego multi-value.
"""

from __future__ import annotations

import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

from google.oauth2.service_account import Credentials
import gspread

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"

COL_TECH_KEY = 0  # Technical_Key
COL_L = 11  # Powertrain_Context (0-indexed)

# ---------------------------------------------------------------------------
# SŁOWNIK: technical_key → właściwa wartość Powertrain_Context
# Wartości muszą istnieć dokładnie w REF_SILNIKI kolumna B
# ---------------------------------------------------------------------------
POWERTRAIN_MAP: dict[str, str] = {
    # --- LPG (instalacja gazowa) ---
    "instalacja_lpg_taknie": "LPG",
    "marka_instalacji_lpg": "LPG",
    "model_instalacji_lpg": "LPG",
    "gwarantinstalator_instalacji_lpg": "LPG",
    "cykl_obowiązkowego_serwisu_instalacji_lpg_w_kmmiesiącach": "LPG",
    "producent_zbiornika_lpg": "LPG",
    "pojemność_zbiornika_lpg_w_litrach": "LPG",
    "nr_fabryczny_zbiornika_lpg": "LPG",
    # --- BEV / Elektryczne ---
    "zasięg_wltp_dla_pojazdów_elektrycznych_w_km": "Elektryczny (BEV)",
    "pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh": "Elektryczny (BEV)",
    # --- PHEV + BEV (funkcja ładowania) - dominujący: BEV ---
    "funkcja_szybkiego_ładowania_samochodu": "Elektryczny (BEV)",
    # --- Cechy wielokrotnego napędu (ICE + PHEV) ---
    # moc_silnika - dotyczy wszystkich napędów (KM jest nawet dla EV) → ALL
    # pojemnosc_silnika - tylko ICE/HEV/PHEV → zostaje ALL (nie ma 'Spalinowy' w słowniku)
    # zużycie_paliwa_wltp_spalinowych → tytuł mówi 'spalinowych'
    "zużycie_paliwa_wltp_dla_silników_spalinowych_w_litrach": "ALL",
    # ↑ zostawiamy ALL - nie wiemy czy to benzyna czy diesel
}


def main() -> None:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws_cechy = ss.worksheet("cechy")

    all_rows = ws_cechy.get_all_values()
    print(f"Cechy: {len(all_rows) - 1} wierszy danych\n")

    cells_to_update: list[gspread.Cell] = []

    for row_idx, row in enumerate(all_rows):
        if row_idx == 0:
            continue  # Pomiń nagłówek

        tech_key = row[COL_TECH_KEY].strip() if row else ""
        if not tech_key:
            continue

        if tech_key not in POWERTRAIN_MAP:
            continue

        desired = POWERTRAIN_MAP[tech_key]
        current = row[COL_L].strip() if len(row) > COL_L else ""

        if current == desired:
            print(f"  ✓ SKIP  {tech_key}: '{current}' już poprawne")
            continue

        print(f"  → SET   {tech_key}: '{current}' → '{desired}'")
        cells_to_update.append(
            gspread.Cell(row=row_idx + 1, col=COL_L + 1, value=desired)
        )

    if not cells_to_update:
        print("\nWszystko już jest poprawne — brak zmian.")
        return

    print(f"\nZapisywanie {len(cells_to_update)} zmian...")
    ws_cechy.update_cells(cells_to_update, value_input_option="RAW")
    print("✅ Gotowe!")

    # Weryfikacja
    print("\n--- Weryfikacja po zmianie ---")
    updated = ws_cechy.get_all_values()
    changed_keys = set(POWERTRAIN_MAP.keys())
    for row in updated[1:]:
        tech_key = row[COL_TECH_KEY].strip() if row else ""
        if tech_key in changed_keys:
            val = row[COL_L].strip() if len(row) > COL_L else ""
            expected = POWERTRAIN_MAP[tech_key]
            status = "✅" if val == expected else "❌"
            print(f"  {status} {tech_key}: '{val}'")


if __name__ == "__main__":
    main()
