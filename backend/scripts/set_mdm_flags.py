"""Ustawia flagi MDM (Is_Filterable, Is_Comparable, Is_Tender_Criteria) w arkuszu cechy.

Reguły:
  CORE        → Filterable=TRUE, Comparable=TRUE, Tender_Criteria=TRUE
  EXTENDED*   → Filterable=TRUE, Comparable=TRUE  (* tylko cechy z EXTENDED_TENDER_KEYS)
  EDGE        → bez zmian (FALSE)

Naprawa dodatkowa:
  kategoria_pojazdu = 'ALL' → '' (puste = dotyczy wszystkich, nie ma w słowniku)

Skrypt idempotentny — bezpieczny do wielokrotnego uruchomienia.
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

# EXTENDED cechy które powinny być filtrowalne i porównywalne
EXTENDED_TENDER_KEYS: frozenset[str] = frozenset(
    {
        # Bezpieczeństwo aktywne
        "abs",
        "esp",
        "asr",
        "aktywny_tempomat",
        "asystent_pasa_ruchu",
        "asystent_zmiany_pasa_ruchu",
        "monitorowanie_martwego_pola",
        "rozpoznawanie_znakow_drogowych",
        "asystent_ruszania_na_wzniesieniach",
        # Kamery i sensory
        "kamera_cofania",
        "czujniki_parkowania_tył",
        "czujniki_parkowania_przod_i_tyl",
        # Komfort
        "klimatyzacja_automatyczna",
        "klimatyzacja_wielostrefowa",
        "klimatyzacja_dla_pasażerów_z_tyłu",
        "podgrzewane_fotele_przednie",
        # Multimedia
        "ekran_dotykowy",
        "gps_nawigacja_satelitarna",
        "apple_carplay_android_auto",
        "apple_car_play",
        "ladowarka_indukcyjna",
        # Dostęp i wygoda
        "bezkluczykowy_dostep",
        "hak_holowniczy",
        "elektrycznie_sterowana_klapa_bagaznika",
        "felga_aluminiowa",
        "liczba_miejsc",
        # Napęd alternatywny
        "zasięg_wltp_dla_pojazdów_elektrycznych_w_km",
        "pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh",
        "funkcja_szybkiego_ładowania_samochodu",
        "zużycie_paliwa_wltp_dla_silników_spalinowych_w_litrach",
        # Dostawcze / wymiary ładunkowe
        "długość_przestrzeni_ładunkowej_w_mm",
        "wysokość_przestrzeni_ładunkowej_w_mm",
        "szerokość_przestrzeni_ładunkowej_w_mm",
        "cargo_volume",
        "cargo_length",
    }
)


def _col(headers: list[str], name: str) -> int:
    name_lower = name.lower()
    for i, h in enumerate(headers):
        if h.strip().lower() == name_lower:
            return i
    raise KeyError(f"Kolumna {name!r} nie znaleziona. Dostępne: {headers}")


def apply_mdm_flags() -> dict[str, int]:
    """Stosuje flagi MDM. Zwraca słownik ze statystykami zmian."""
    creds = Credentials.from_service_account_file(
        SA_KEY_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(SPREADSHEET_ID).worksheet("cechy")

    all_rows = ws.get_all_values()
    headers = [h.strip() for h in all_rows[0]]

    c_key = _col(headers, "Technical_Key")
    c_tier = _col(headers, "Feature_Tier")
    c_kat = _col(headers, "kategoria_pojazdu")
    c_filt = _col(headers, "Is_Filterable")
    c_tender = _col(headers, "Is_Tender_Criteria")
    c_comp = _col(headers, "Is_Comparable")

    cells: list[gspread.Cell] = []
    stats: dict[str, int] = {
        "filterable": 0,
        "tender": 0,
        "comparable": 0,
        "kat_fixed": 0,
    }

    for row_idx, row in enumerate(all_rows[1:], start=2):
        max_col = max(c_kat, c_filt, c_tender, c_comp)
        while len(row) <= max_col:
            row.append("")

        tech_key = row[c_key].strip()
        tier = row[c_tier].strip().upper()
        if not tech_key:
            continue

        # Naprawa Kategoria_Pojazdu
        if row[c_kat].strip() == "ALL":
            cells.append(gspread.Cell(row=row_idx, col=c_kat + 1, value=""))
            stats["kat_fixed"] += 1

        def _set(col_idx: int, key: str) -> None:
            if row[col_idx].strip().upper() != "TRUE":
                cells.append(gspread.Cell(row=row_idx, col=col_idx + 1, value="TRUE"))
                stats[key] += 1

        if tier == "CORE":
            _set(c_filt, "filterable")
            _set(c_tender, "tender")
            _set(c_comp, "comparable")

        elif tier == "EXTENDED" and tech_key in EXTENDED_TENDER_KEYS:
            _set(c_filt, "filterable")
            _set(c_comp, "comparable")

    if cells:
        ws.update_cells(cells, value_input_option="RAW")
        logger.info("Zaktualizowano %d komórek: %s", len(cells), stats)
    else:
        logger.info("Brak zmian — wszystko aktualne.")

    return stats


if __name__ == "__main__":
    result = apply_mdm_flags()
    print(f"Wynik: {result}")
