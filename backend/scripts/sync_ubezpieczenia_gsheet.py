import os
import sys
import pandas as pd
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from core.database import supabase

SHEET_URL = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=61577885"
TABLE_NAME = "ltr_admin_ubezpieczenia"


def main():
    print("Pobieranie danych o klasach SAMAR w celu zmapowania nazw na FK...")
    classes_res = supabase.table("samar_classes").select("id, name").execute()
    class_map = {c["name"].strip().lower(): c["id"] for c in classes_res.data}

    print("Pobieranie danych z Google Sheets (zakładka gid=61577885)...")
    try:
        df = pd.read_csv(SHEET_URL, encoding="utf-8")
        df = df.fillna("")
        df.columns = [str(c).strip() for c in df.columns]

        records = df.to_dict(orient="records")
        db_records = []

        for r in records:
            # Mapowanie stringa "Lekkie dostawcze - KOMBI VAN" na integer FK
            class_name = str(r.get("Klasa SAMAR (FK)", "")).strip().lower()
            if not class_name:
                continue

            klasa_fk = class_map.get(class_name)
            if klasa_fk is None:
                # Nie znaleziono klasy, pomijamy lub wstawiamy None
                print(
                    f"Ostrzeżenie: Nie znaleziono klasy SAMAR: '{class_name}'. Pomijam wiersz."
                )
                continue

            rok = r.get("Rok")
            stawka_ac = r.get("Stawka Bazowa AC")
            skladka_oc = r.get("Składka OC (zł)")
            wsp_przebieg = r.get("Wsp. Średni Przebieg")
            wsp_szkody = r.get("Wsp. Wartość Szkody")

            # Formatowanie liczb (np. z przecinkiem "0,015" na float 0.015)
            def to_float(val):
                if val == "":
                    return None
                if isinstance(val, str):
                    val = val.replace(",", ".").replace(" ", "")
                try:
                    return float(val)
                except:
                    return None

            def to_int(val):
                if val == "":
                    return None
                try:
                    return int(val)
                except:
                    return None

            db_records.append(
                {
                    "klasa_samar_fk": klasa_fk,
                    "rok": to_int(rok),
                    "stawka_bazowa_ac": to_float(stawka_ac),
                    "skladka_oc_zl": to_float(skladka_oc),
                    "wsp_sredni_przebieg": to_float(wsp_przebieg),
                    "wsp_wartosc_szkody": to_float(wsp_szkody),
                }
            )

        print(f"Rozpoczynam zrzut danych do tabeli {TABLE_NAME} (Online)...")
        # Zamiast delete() użyjemy metody czyszczenia - brak filtru jest niedozwolony w supabase RLS
        # Dla UUID nie zadziała id>=0, więc filtrujemy po "rok > 0" bo zawsze tam jest coś
        delete_response = (
            supabase.table(TABLE_NAME).delete().neq("rok", -9999).execute()
        )
        print(f"Usunięto stare rekordy: {len(delete_response.data)}")

        batch_size = 100
        inserted = 0
        for i in range(0, len(db_records), batch_size):
            batch = db_records[i : i + batch_size]
            res = supabase.table(TABLE_NAME).insert(batch).execute()
            inserted += len(res.data)

        print(f"✅ SUKCES! Wgrano {inserted} stawek ubezpieczeniowych do bazy.")

    except Exception as e:
        print(f"❌ Błąd podczas synchronizacji: {e}")


if __name__ == "__main__":
    main()
