"""Kompleksowa naprawa arkusza cechy:

1. Ustawienie Is_Filterable=TRUE, Is_Comparable=TRUE, Is_Tender_Criteria=TRUE
   dla cech CORE (23 sztuk)
2. Ustawienie Is_Filterable=TRUE, Is_Comparable=TRUE dla kluczowych EXTENDED
3. Weryfikacja Kategoria_Pojazdu — dopuszczalne: 'Osobowy', 'Ciężarowy', '' (puste)
   Wartość 'ALL' nie jest w słowniku → zastąpić pustą (= wszystkie)

Skrypt idempotentny, bezpieczny do wielokrotnego uruchomienia.
"""

from __future__ import annotations

import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"

# ---------------------------------------------------------------------------
# EXTENDED cechy które są ważne przetargowo / filtracyjnie
# (na podstawie analizy semantycznej nazw)
# ---------------------------------------------------------------------------
EXTENDED_TENDER_KEYS: set[str] = {
    # Bezpieczeństwo
    "kamera_cofania",
    "czujniki_parkowania_tył",
    "czujniki_parkowania_przod_i_tyl",
    "aktywny_tempomat",
    "asystent_pasa_ruchu",
    "monitorowanie_martwego_pola",
    "asystent_zmiany_pasa_ruchu",
    "rozpoznawanie_znakow_drogowych",
    "abs",
    "esp",
    "asr",
    # Komfort kluczowy
    "klimatyzacja_automatyczna",
    "klimatyzacja_wielostrefowa",
    "klimatyzacja_dla_pasażerów_z_tyłu",
    "podgrzewane_fotele_przednie",
    "ekran_dotykowy",
    "nawigacja_gps",
    "apple_carplay_android_auto",
    "apple_car_play",
    "ladowarka_indukcyjna",
    "bezkluczykowy_dostep",
    # Wyposażenie praktyczne
    "hak_holowniczy",
    "felga_aluminiowa",
    "liczba_miejsc",
    "elektrycznie_sterowana_klapa_bagaznika",
    # Napęd i efektywność
    "zasięg_wltp_dla_pojazdów_elektrycznych_w_km",
    "pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh",
    "funkcja_szybkiego_ładowania_samochodu",
    "zużycie_paliwa_wltp_dla_silników_spalinowych_w_litrach",
    # Dostawcze
    "długość_przestrzeni_ładunkowej_w_mm",
    "wysokość_przestrzeni_ładunkowej_w_mm",
    "szerokość_przestrzeni_ładunkowej_w_mm",
    "cargo_volume",
    "cargo_length",
}


def _col(headers: list[str], name: str) -> int:
    """Zwraca 0-indexed numer kolumny. Szuka case-insensitive."""
    name_lower = name.lower()
    for i, h in enumerate(headers):
        if h.strip().lower() == name_lower:
            return i
    raise KeyError(f"Nie znaleziono kolumny: {name!r}. Dostępne: {headers}")


def main() -> None:
    creds = Credentials.from_service_account_file(
        SA_KEY_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = ss.worksheet("cechy")

    all_rows = ws.get_all_values()
    headers = [h.strip() for h in all_rows[0]]

    # Indeksy kolumn
    c_key = _col(headers, "Technical_Key")
    c_tier = _col(headers, "Feature_Tier")
    c_kat = _col(headers, "kategoria_pojazdu")  # małe litery!
    c_filterable = _col(headers, "Is_Filterable")
    c_tender = _col(headers, "Is_Tender_Criteria")
    c_comparable = _col(headers, "Is_Comparable")

    print(
        f"Kolumny: key={c_key} tier={c_tier} kat={c_kat} "
        f"filterable={c_filterable} tender={c_tender} comparable={c_comparable}"
    )

    cells_to_update: list[gspread.Cell] = []
    stats = {"filterable_set": 0, "tender_set": 0, "comparable_set": 0, "kat_fixed": 0}

    for row_idx, row in enumerate(all_rows[1:], start=2):
        while len(row) <= max(c_kat, c_filterable, c_tender, c_comparable):
            row.append("")

        tech_key = row[c_key].strip()
        tier = row[c_tier].strip().upper()
        kat = row[c_kat].strip()

        if not tech_key:
            continue

        # ----------------------------------------------------------------
        # 1. Naprawa Kategoria_Pojazdu: 'ALL' → '' (puste = wszystkie)
        # ----------------------------------------------------------------
        if kat == "ALL":
            cells_to_update.append(gspread.Cell(row=row_idx, col=c_kat + 1, value=""))
            stats["kat_fixed"] += 1

        # ----------------------------------------------------------------
        # 2. CORE → Is_Filterable=TRUE, Is_Comparable=TRUE, Is_Tender_Criteria=TRUE
        # ----------------------------------------------------------------
        if tier == "CORE":
            if row[c_filterable].strip().upper() != "TRUE":
                cells_to_update.append(
                    gspread.Cell(row=row_idx, col=c_filterable + 1, value="TRUE")
                )
                stats["filterable_set"] += 1

            if row[c_tender].strip().upper() != "TRUE":
                cells_to_update.append(
                    gspread.Cell(row=row_idx, col=c_tender + 1, value="TRUE")
                )
                stats["tender_set"] += 1

            if row[c_comparable].strip().upper() != "TRUE":
                cells_to_update.append(
                    gspread.Cell(row=row_idx, col=c_comparable + 1, value="TRUE")
                )
                stats["comparable_set"] += 1

        # ----------------------------------------------------------------
        # 3. Kluczowe EXTENDED → Is_Filterable=TRUE, Is_Comparable=TRUE
        # ----------------------------------------------------------------
        elif tier == "EXTENDED" and tech_key in EXTENDED_TENDER_KEYS:
            if row[c_filterable].strip().upper() != "TRUE":
                cells_to_update.append(
                    gspread.Cell(row=row_idx, col=c_filterable + 1, value="TRUE")
                )
                stats["filterable_set"] += 1

            if row[c_comparable].strip().upper() != "TRUE":
                cells_to_update.append(
                    gspread.Cell(row=row_idx, col=c_comparable + 1, value="TRUE")
                )
                stats["comparable_set"] += 1

    # ----------------------------------------------------------------
    # Zapis
    # ----------------------------------------------------------------
    print(f"\nDo zaktualizowania: {len(cells_to_update)} komórek")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if not cells_to_update:
        print("Brak zmian — wszystko aktualne.")
        return

    print("\nZapis batch...")
    ws.update_cells(cells_to_update, value_input_option="RAW")
    print("✅ Zakończono!")

    # ----------------------------------------------------------------
    # Weryfikacja końcowa
    # ----------------------------------------------------------------
    print("\n--- Weryfikacja ---")
    updated = ws.get_all_values()
    core_ok = ext_ok = 0
    core_fail: list[str] = []

    for row in updated[1:]:
        while len(row) <= max(c_filterable, c_tender, c_comparable):
            row.append("")
        key = row[c_key].strip()
        tier = row[c_tier].strip().upper()

        if tier == "CORE":
            if (
                row[c_filterable].upper() == "TRUE"
                and row[c_tender].upper() == "TRUE"
                and row[c_comparable].upper() == "TRUE"
            ):
                core_ok += 1
            else:
                core_fail.append(
                    f"{key}: F={row[c_filterable]} T={row[c_tender]} C={row[c_comparable]}"
                )

        elif tier == "EXTENDED" and key in EXTENDED_TENDER_KEYS:
            if (
                row[c_filterable].upper() == "TRUE"
                and row[c_comparable].upper() == "TRUE"
            ):
                ext_ok += 1

    print(f"  CORE poprawne: {core_ok}/23")
    if core_fail:
        print("  CORE błędy:")
        for f in core_fail:
            print(f"    ❌ {f}")

    print(f"  EXTENDED (kluczowe) poprawne: {ext_ok}/{len(EXTENDED_TENDER_KEYS)}")


if __name__ == "__main__":
    main()
