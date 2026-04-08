"""Pełny audyt arkusza cechy — weryfikacja wszystkich wierszy.

Sprawdza:
1. Kompletność wymaganych kolumn (Technical_Key, Functional_Name, Data_Type)
2. Poprawność Feature_Tier (CORE/EXTENDED/EDGE)
3. Poprawność Kategoria_Pojazdu
4. Poprawność Powertrain_Context vs REF_SILNIKI
5. Poprawność Drivetrain_Context vs suspension_dict
6. Spójność flagów boolean (True/False/puste)
7. Statystyki rozkładu wartości
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

from google.oauth2.service_account import Credentials
import gspread

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"

BOOL_COLS = [
    "Is_Filterable",
    "Is_Tender_Criteria",
    "Required_For_Tender",
    "Is_Derived",
    "Is_Contextual",
    "Is_Mandatory_For_Matching",
    "Is_Comparable",
    "Data_Confidence_Required",
]
VALID_BOOL = {"TRUE", "FALSE", ""}
VALID_TIERS = {"CORE", "EXTENDED", "EDGE", ""}
VALID_CATEGORIES = {"Osobowe", "Ciężarowe", "Wszystkie", ""}


def main() -> None:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    ws_cechy = ss.worksheet("cechy")
    ref_silniki = {
        row[1].strip()
        for row in ss.worksheet("REF_SILNIKI").get_all_values()[1:]
        if len(row) > 1 and row[1].strip()
    }
    ref_silniki |= {"ALL", ""}

    susp_dict = {
        row[1].strip()
        for row in ss.worksheet("suspension_dict").get_all_values()[1:]
        if len(row) > 1 and row[1].strip()
    }
    susp_dict |= {"ALL", ""}

    all_rows = ws_cechy.get_all_values()
    headers = [h.strip() for h in all_rows[0]]
    col = {h: i for i, h in enumerate(headers)}

    print(f"Nagłówki ({len(headers)}): {headers}\n")

    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, dict] = defaultdict(lambda: defaultdict(int))

    for row_idx, row in enumerate(all_rows[1:], start=2):
        # Extend wierszu
        while len(row) < len(headers):
            row.append("")

        tech_key = row[col.get("Technical_Key", 0)].strip()
        if not tech_key:
            continue

        func_name = row[col.get("Functional_Name", 1)].strip()
        data_type = row[col.get("Data_Type", 3)].strip()
        tier = row[col.get("Feature_Tier", 8)].strip().upper()
        kat = row[col.get("Kategoria_Pojazdu", 9)].strip()
        powertrain = row[col.get("Powertrain_Context", 11)].strip()
        drivetrain = row[col.get("Drivetrain_Context", 12)].strip()

        # --- Wymagane pola ---
        if not func_name:
            warnings.append(f"Wiersz {row_idx} ({tech_key}): brak Functional_Name")
        if not data_type:
            warnings.append(f"Wiersz {row_idx} ({tech_key}): brak Data_Type")
        if not tier:
            warnings.append(f"Wiersz {row_idx} ({tech_key}): brak Feature_Tier")

        # --- Poprawność wartości ---
        if tier not in VALID_TIERS:
            errors.append(
                f"Wiersz {row_idx} ({tech_key}): nieprawidłowy Feature_Tier='{tier}'"
            )

        if kat not in VALID_CATEGORIES:
            errors.append(
                f"Wiersz {row_idx} ({tech_key}): nieprawidłowa Kategoria_Pojazdu='{kat}'"
            )

        if powertrain not in ref_silniki:
            errors.append(
                f"Wiersz {row_idx} ({tech_key}): Powertrain_Context='{powertrain}' nie w REF_SILNIKI"
            )

        if drivetrain not in susp_dict:
            errors.append(
                f"Wiersz {row_idx} ({tech_key}): Drivetrain_Context='{drivetrain}' nie w suspension_dict"
            )

        # --- Flagi boolean ---
        for flag in BOOL_COLS:
            if flag not in col:
                continue
            val = row[col[flag]].strip().upper()
            if val not in VALID_BOOL:
                errors.append(
                    f"Wiersz {row_idx} ({tech_key}): {flag}='{row[col[flag]]}' nie jest TRUE/FALSE"
                )
            stats[flag][val] += 1

        # --- Statystyki ---
        stats["Feature_Tier"][tier or "(puste)"] += 1
        stats["Kategoria_Pojazdu"][kat or "(puste)"] += 1
        stats["Powertrain_Context"][powertrain or "(puste)"] += 1
        stats["Drivetrain_Context"][drivetrain or "(puste)"] += 1

    # ========= RAPORT =========
    SEP = "=" * 65

    print(SEP)
    print(f"BŁĘDY ({len(errors)}):")
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
    else:
        print("  Brak błędów!")

    print(f"\n{SEP}")
    print(f"OSTRZEŻENIA ({len(warnings)}):")
    if warnings:
        for w in warnings[:20]:
            print(f"  ⚠️  {w}")
        if len(warnings) > 20:
            print(f"  ... i {len(warnings) - 20} więcej")
    else:
        print("  Brak ostrzeżeń!")

    print(f"\n{SEP}")
    print("STATYSTYKI ROZKŁADU:")
    for col_name, dist in stats.items():
        print(f"\n  {col_name}:")
        for val, cnt in sorted(dist.items(), key=lambda x: -x[1]):
            print(f"    '{val}': {cnt}")


if __name__ == "__main__":
    main()
