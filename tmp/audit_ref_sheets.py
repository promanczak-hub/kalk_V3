"""Audyt zawartości arkuszy referencyjnych i kolumn L/M w cechy."""

import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

from google.oauth2.service_account import Credentials
import gspread

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"


def read_sheet_safe(ss: gspread.Spreadsheet, name: str) -> list[list[str]]:
    try:
        ws = ss.worksheet(name)
        return ws.get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        return []


def main() -> None:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    # --- Lista wszystkich arkuszy ---
    all_worksheets = [ws.title for ws in ss.worksheets()]
    print("=" * 60)
    print(f"WSZYSTKIE ARKUSZE W SPREADSHEET ({len(all_worksheets)}):")
    for ws_name in all_worksheets:
        print(f"  - {ws_name}")

    # --- Zawartość REF_SILNIKI ---
    print("\n" + "=" * 60)
    ref_silniki = read_sheet_safe(ss, "REF_SILNIKI")
    if ref_silniki:
        print(f"REF_SILNIKI ({len(ref_silniki)} wierszy łącznie z nagłówkiem):")
        for i, row in enumerate(ref_silniki[:20]):
            print(f"  [{i}] {row}")
    else:
        print("REF_SILNIKI: BRAK ARKUSZA!")

    # --- Zawartość suspension_dict ---
    print("\n" + "=" * 60)
    susp = read_sheet_safe(ss, "suspension_dict")
    if susp:
        print(f"suspension_dict ({len(susp)} wierszy):")
        for i, row in enumerate(susp[:20]):
            print(f"  [{i}] {row}")
    else:
        print("suspension_dict: BRAK ARKUSZA!")

    # --- Zawartość ref_drivetrain (jeśli istnieje) ---
    print("\n" + "=" * 60)
    ref_drv = read_sheet_safe(ss, "ref_drivetrain")
    if ref_drv:
        print(f"ref_drivetrain ({len(ref_drv)} wierszy):")
        for i, row in enumerate(ref_drv[:10]):
            print(f"  [{i}] {row}")
    else:
        print("ref_drivetrain: BRAK ARKUSZA!")

    # --- Analiza kolumn L i M w cechy ---
    print("\n" + "=" * 60)
    cechy = read_sheet_safe(ss, "cechy")
    if not cechy or len(cechy) < 2:
        print("cechy: BRAK DANYCH!")
        return

    headers = cechy[0]
    print(f"Nagłówki cechy (pierwsze 15): {headers[:15]}")

    # Znajdź indeksy kolumn L (11) i M (12)
    col_l_idx = 11  # 0-indexed
    col_m_idx = 12

    powertrain_values: dict[str, int] = {}
    drivetrain_values: dict[str, int] = {}

    for row in cechy[1:]:
        if len(row) > col_l_idx:
            v = row[col_l_idx].strip()
            powertrain_values[v] = powertrain_values.get(v, 0) + 1
        if len(row) > col_m_idx:
            v = row[col_m_idx].strip()
            drivetrain_values[v] = drivetrain_values.get(v, 0) + 1

    print("\nKolumna L (Powertrain_Context) — unikalne wartości:")
    for val, cnt in sorted(powertrain_values.items(), key=lambda x: -x[1]):
        marker = "  ✓" if val in ("ALL", "") else "  ?"
        print(f"{marker} '{val}' x{cnt}")

    print("\nKolumna M (Drivetrain_Context) — unikalne wartości:")
    for val, cnt in sorted(drivetrain_values.items(), key=lambda x: -x[1]):
        marker = "  ✓" if val in ("ALL", "") else "  ?"
        print(f"{marker} '{val}' x{cnt}")


if __name__ == "__main__":
    main()
