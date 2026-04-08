"""Naprawa danych w kolumnach Powertrain_Context (L) i Drivetrain_Context (M).

Strategia:
- Kolumna L: wartości inne niż dozwolone (TRUE/FALSE/multi) → 'ALL'
  Dozwolone: puste, 'ALL', dokładne nazwy z REF_SILNIKI kolumna B
- Kolumna M: wszystkie wartości błędne (TRUE/FALSE/manual,automatic) → 'ALL'
  Dozwolone: puste, 'ALL', wartości z suspension_dict kolumna B

Logika: Lepiej mieć 'ALL' (defensywne) niż zostawić błędne dane.
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

# Kolumny 0-indexed
COL_L = 11  # Powertrain_Context
COL_M = 12  # Drivetrain_Context


def main() -> None:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    # 1. Wczytaj dozwolone wartości ze słowników
    ref_silniki_ws = ss.worksheet("REF_SILNIKI")
    allowed_powertrain: set[str] = {
        row[1].strip()
        for row in ref_silniki_ws.get_all_values()[1:]
        if len(row) > 1 and row[1].strip()
    }
    allowed_powertrain.add("ALL")
    allowed_powertrain.add("")
    print(f"Dozwolone Powertrain: {sorted(allowed_powertrain)}")

    susp_ws = ss.worksheet("suspension_dict")
    allowed_drivetrain: set[str] = {
        row[1].strip()
        for row in susp_ws.get_all_values()[1:]
        if len(row) > 1 and row[1].strip()
    }
    allowed_drivetrain.add("ALL")
    allowed_drivetrain.add("")
    print(f"Dozwolone Drivetrain: {sorted(allowed_drivetrain)}")

    # 2. Wczytaj arkusz cechy
    ws_cechy = ss.worksheet("cechy")
    all_rows = ws_cechy.get_all_values()
    print(f"\nCechy: {len(all_rows)} wierszy (łącznie z nagłówkiem)")

    # 3. Przygotuj korekty
    cells_to_fix: list[gspread.Cell] = []
    stats = {"powertrain_fixed": 0, "drivetrain_fixed": 0}

    for row_idx, row in enumerate(all_rows):
        if row_idx == 0:
            continue  # Pomiń nagłówek

        # Extend wierszu jeśli za krótki
        while len(row) <= COL_M:
            row.append("")

        tech_key = row[0].strip() if row else ""

        # --- Kolumna L (Powertrain_Context) ---
        pow_val = row[COL_L].strip()
        if pow_val not in allowed_powertrain:
            print(
                f"  Wiersz {row_idx + 1} ({tech_key}): Powertrain '{pow_val}' → 'ALL'"
            )
            cells_to_fix.append(
                gspread.Cell(row=row_idx + 1, col=COL_L + 1, value="ALL")
            )
            stats["powertrain_fixed"] += 1

        # --- Kolumna M (Drivetrain_Context) ---
        drv_val = row[COL_M].strip()
        if drv_val not in allowed_drivetrain:
            print(
                f"  Wiersz {row_idx + 1} ({tech_key}): Drivetrain '{drv_val}' → 'ALL'"
            )
            cells_to_fix.append(
                gspread.Cell(row=row_idx + 1, col=COL_M + 1, value="ALL")
            )
            stats["drivetrain_fixed"] += 1

    print(f"\nDo naprawy: {len(cells_to_fix)} komórek")
    print(f"  Powertrain: {stats['powertrain_fixed']}")
    print(f"  Drivetrain: {stats['drivetrain_fixed']}")

    if not cells_to_fix:
        print("Wszystko już jest poprawne!")
        return

    # 4. Batch update
    print("Zapisywanie napraw...")
    ws_cechy.update_cells(cells_to_fix, value_input_option="RAW")
    print("✅ Naprawa zakończona!")

    # 5. Weryfikacja końcowa
    print("\n--- Weryfikacja po naprawie ---")
    updated_rows = ws_cechy.get_all_values()
    pow_vals: dict[str, int] = {}
    drv_vals: dict[str, int] = {}
    for row in updated_rows[1:]:
        if len(row) > COL_L:
            v = row[COL_L].strip()
            pow_vals[v] = pow_vals.get(v, 0) + 1
        if len(row) > COL_M:
            v = row[COL_M].strip()
            drv_vals[v] = drv_vals.get(v, 0) + 1

    print("Powertrain_Context po naprawie:")
    for v, c in sorted(pow_vals.items(), key=lambda x: -x[1]):
        status = "✅" if v in allowed_powertrain else "❌"
        print(f"  {status} '{v}' x{c}")

    print("Drivetrain_Context po naprawie:")
    for v, c in sorted(drv_vals.items(), key=lambda x: -x[1]):
        status = "✅" if v in allowed_drivetrain else "❌"
        print(f"  {status} '{v}' x{c}")


if __name__ == "__main__":
    main()
