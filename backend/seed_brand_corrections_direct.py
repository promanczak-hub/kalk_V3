"""
Direct seeder for brand corrections from Excel KOR. MARKA.
Bypasses the old seed_body_and_brand_corrections.py which has stale schema.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

from core.database import supabase
from seed_depreciation_rates import CLASS_MAP, FUEL_SUFFIX_MAP

EXCEL_PATH = Path(
    r"C:\Users\proma\Downloads"
    r"\DRAFT KALKULATORA WARTOŚCI REZYDUALNYCH"
    r" ver aktualna JŁ 02.02 (version 1).xlsx"
)


def main() -> None:
    print("Opening Excel...")
    wb = openpyxl.load_workbook(str(EXCEL_PATH), data_only=True)
    ws = wb["KOR. MARKA"]

    records: list[dict] = []
    skipped = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        class_code = row[0]
        brand = row[1]
        fuel = row[2]
        korekta = row[4]

        if not class_code or not brand:
            continue
        if not isinstance(class_code, str):
            continue

        # Resolve class
        samar_id = CLASS_MAP.get(str(class_code).strip())
        if samar_id is None:
            for k, v in CLASS_MAP.items():
                if k.upper() == str(class_code).strip().upper():
                    samar_id = v
                    break
        if samar_id is None:
            skipped += 1
            continue

        fuel_id = FUEL_SUFFIX_MAP.get(str(fuel).strip())
        if fuel_id is None:
            skipped += 1
            continue

        records.append(
            {
                "klasa_wr_id": samar_id,
                "rodzaj_paliwa": fuel_id,
                "brand_name": str(brand).strip().upper(),
                "korekta_procent": float(korekta) if korekta else 0.0,
            }
        )

    print(f"Read {len(records)} corrections, skipped {skipped}")

    # Insert one at a time to debug failures
    ok = 0
    errors = 0
    for rec in records:
        try:
            supabase.table("ltr_admin_korekta_wr_markas").insert(rec).execute()
            ok += 1
        except Exception as e:
            emsg = str(e)[:80]
            if "duplicate" in emsg.lower() or "23505" in emsg:
                # Already exists — try upsert
                try:
                    supabase.table("ltr_admin_korekta_wr_markas").upsert(
                        rec,
                        on_conflict="klasa_wr_id,rodzaj_paliwa,brand_name",
                    ).execute()
                    ok += 1
                except Exception as e2:
                    errors += 1
                    if errors <= 3:
                        print(f"  ERR upsert: {rec} -> {e2}")
            else:
                errors += 1
                if errors <= 3:
                    print(f"  ERR: {rec} -> {emsg}")

    print(f"\nDone: {ok} OK, {errors} errors")

    # Verify
    r = supabase.table("ltr_admin_korekta_wr_markas").select("*").limit(0).execute()


if __name__ == "__main__":
    main()
