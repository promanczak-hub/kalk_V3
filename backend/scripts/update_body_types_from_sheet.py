import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.database import supabase


def update_body_types():
    url = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=484265370"
    print(f"Pobieranie danych z Google Sheets: {url}")
    df = pd.read_csv(url)

    updates_count = 0

    print("Rozpoczynam synchronizacje nadwozi...")
    for index, row in df.iterrows():
        b_id = row["ID"]
        b_name = row["Nazwa_Nadwozia"]
        b_type = row["Typ_Pojazdu"]

        # update the db
        res = (
            supabase.table("body_types")
            .update({"vehicle_class": b_type})
            .eq("id", b_id)
            .execute()
        )

        if res.data:
            print(f"Zaktualizowano ID {b_id} ({b_name}) -> {b_type}")
            updates_count += 1
        else:
            print(f"Nie znaleziono ID {b_id} w bazie.")

    print(f"\nGotowe! Zaktualizowano {updates_count} rekordów w tabeli body_types.")


if __name__ == "__main__":
    update_body_types()
