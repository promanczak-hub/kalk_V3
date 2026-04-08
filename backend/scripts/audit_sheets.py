import os
import re
import sys

from google.oauth2.service_account import Credentials
import gspread

# We need to run django/fastapi environment? We can just use the supabase client.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.database import supabase


def audit_sheet():
    # 1. Fetch body types
    body_types_result = (
        supabase.table("body_types").select("id, nazwa_nadwozia, typ_pojazdu").execute()
    )
    body_types_dict = {
        bt["nazwa_nadwozia"].strip().upper(): bt for bt in body_types_result.data
    }

    # 2. Fetch sheet
    key_path = "D:/kalk_v3/backend/google_sa_key.json"
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key("1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q")
    ws = ss.worksheet("cechy")

    data = ws.get_all_values()
    headers = [h.strip().lower() for h in data[0]]
    col_idx = {h: i for i, h in enumerate(headers)}

    if (
        "technical_key" not in col_idx
        or "body_context" not in col_idx
        or "kategoria_pojazdu" not in col_idx
    ):
        print("Brak kolumn w arkuszu.")
        return

    errors = []

    for idx, row in enumerate(data[1:], start=2):
        if len(row) <= col_idx["technical_key"]:
            continue
        tech_key = row[col_idx["technical_key"]].strip()
        if not tech_key:
            continue

        kat_raw = (
            row[col_idx["kategoria_pojazdu"]].strip().lower()
            if len(row) > col_idx["kategoria_pojazdu"]
            else ""
        )
        if kat_raw in ("osobowe", "passenger"):
            veh_cat = "PASSENGER"
        elif kat_raw in ("ciężarowe", "dostawcze", "commercial"):
            veh_cat = "COMMERCIAL"
        else:
            veh_cat = "ALL"

        raw_body = (
            row[col_idx["body_context"]].strip()
            if len(row) > col_idx["body_context"]
            else ""
        )

        if raw_body and raw_body.upper() not in ("ALL", "WSZYSTKIE", "WSZYSTKO"):
            parts = [p.strip() for p in re.split(r"[/,]", raw_body) if p.strip()]
            for p in parts:
                is_exclusion = p.startswith(("!", "-"))
                p_clean = p[1:].strip().upper() if is_exclusion else p.upper()

                if p_clean not in body_types_dict:
                    errors.append(
                        f"Wiersz {idx} ({tech_key}): Nieznany typ nadwozia '{p_clean}'"
                    )
                    continue

                bt_data = body_types_dict[p_clean]
                if veh_cat == "PASSENGER" and bt_data.get("typ_pojazdu") != "Osobowy":
                    errors.append(
                        f"Wiersz {idx} ({tech_key}): Kategoria Osobowe blokuje ciężarowe nadwozie '{p_clean}'"
                    )
                elif (
                    veh_cat == "COMMERCIAL"
                    and bt_data.get("typ_pojazdu") != "Ciężarowy"
                ):
                    errors.append(
                        f"Wiersz {idx} ({tech_key}): Kategoria Ciężarowe blokuje osobowe nadwozie '{p_clean}'"
                    )

    if errors:
        print("Znaleziono potencjalne błędy w konfiguracji nadwozi:")
        for e in errors:
            print("- " + e)
    else:
        print("Wszystko wygląda poprawnie!")


if __name__ == "__main__":
    audit_sheet()
