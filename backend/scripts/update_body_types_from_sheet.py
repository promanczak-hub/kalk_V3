import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.database import supabase


def update_body_types():
    url = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=484265370"
    print(f"Pobieranie danych z Google Sheets: {url}")
    df = pd.read_csv(url)

    # Snapshot DB BEFORE sync so we can categorize rows as added/updated/unchanged.
    existing = (
        supabase.table("body_types")
        .select("id,nazwa_nadwozia,vehicle_class")
        .execute()
        .data
        or []
    )
    db_idx = {r["id"]: r for r in existing}

    added = 0
    updated = 0
    unchanged = 0

    print("Rozpoczynam synchronizacje nadwozi...")
    for _, row in df.iterrows():
        b_id = int(row["ID"])
        b_name = str(row["Nazwa_Nadwozia"]).strip()
        b_type = str(row["Typ_Pojazdu"]).strip()

        prior = db_idx.get(b_id)
        payload = {"id": b_id, "nazwa_nadwozia": b_name, "vehicle_class": b_type}
        supabase.table("body_types").upsert(payload).execute()

        if prior is None:
            added += 1
            print(f"+ Dodano ID {b_id}: {b_name} -> {b_type}")
        elif (
            (prior.get("nazwa_nadwozia") or "").strip() != b_name
            or (prior.get("vehicle_class") or "").strip() != b_type
        ):
            updated += 1
            print(
                f"~ Zaktualizowano ID {b_id}: "
                f"name={prior.get('nazwa_nadwozia')!r}->{b_name!r}, "
                f"class={prior.get('vehicle_class')!r}->{b_type!r}"
            )
        else:
            unchanged += 1

    sot_ids = {int(r["ID"]) for _, r in df.iterrows()}
    orphans = [r for r in existing if r["id"] not in sot_ids]

    print(
        f"\nGotowe! added={added}, updated={updated}, unchanged={unchanged}, "
        f"in_db_not_in_sot={len(orphans)}"
    )
    if orphans:
        print("Wiersze w DB poza SOT (kandydaci do usunięcia ręcznego):")
        for r in orphans:
            print(f"  - id={r['id']}: {r.get('nazwa_nadwozia')!r} / {r.get('vehicle_class')!r}")


if __name__ == "__main__":
    update_body_types()
