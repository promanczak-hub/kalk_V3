import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import supabase


def migrate():
    print("Fetching Samar Classes...")
    classes_resp = supabase.table("samar_classes").select("id, name").execute()
    samar_class_map = {
        row["name"].strip().lower(): row["id"] for row in classes_resp.data
    }
    print(f"Loaded {len(samar_class_map)} samar classes.")

    print("Fetching excel draft TAB. PRZEBIEG...")
    draft_resp = (
        supabase.table("excel_drafts")
        .select("data_rows")
        .eq("sheet_name", "TAB. PRZEBIEG")
        .execute()
    )
    if not draft_resp.data:
        print("No draft found for TAB. PRZEBIEG.")
        return

    data_rows = draft_resp.data[0].get("data_rows", [])

    records_to_insert = []

    for idx, row in enumerate(data_rows):
        klasa_str = str(row.get("col_1", "")).strip()
        if not klasa_str:
            continue

        class_id = samar_class_map.get(klasa_str.lower())
        if not class_id:
            print(f"[{idx}] WARNING: Could not find samar class: '{klasa_str}'")
            continue

        try:
            # Parse `190000.0` or `190000` to int
            max_mileage_str = (
                str(row.get("col_2", "0")).replace(" ", "").replace(",", ".")
            )
            max_mileage = int(float(max_mileage_str))
        except Exception:
            max_mileage = 0

        try:
            c_below_str = str(row.get("col_3", "0")).replace(",", ".")
            c_below = float(c_below_str)
        except Exception:
            c_below = 0.0

        try:
            c_above_str = str(row.get("col_4", "0")).replace(",", ".")
            c_above = float(c_above_str)
        except Exception:
            c_above = 0.0

        records_to_insert.append(
            {
                "samar_class_id": class_id,
                "max_mileage_target": max_mileage,
                "correction_below_threshold": c_below,
                "correction_above_threshold": c_above,
            }
        )

    print(f"Prepared {len(records_to_insert)} records to insert.")
    if records_to_insert:
        try:
            # Delete existing to prevent unique constraint errors during script retry
            supabase.table("samar_mileage_adjustments").delete().neq(
                "id", "00000000-0000-0000-0000-000000000000"
            ).execute()

            resp = (
                supabase.table("samar_mileage_adjustments")
                .insert(records_to_insert)
                .execute()
            )
            print(
                f"Successfully inserted {len(resp.data)} records into samar_mileage_adjustments."
            )
        except Exception as e:
            print(f"ERROR inserting records: {e}")


if __name__ == "__main__":
    migrate()
