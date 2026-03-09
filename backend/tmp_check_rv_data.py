import asyncio
from core.database import supabase


async def check_data():
    try:
        print("--- SPRAWDZANIE DANYCH RV ---")

        # 1. Klasy SAMAR
        res = supabase.table("samar_classes").select("id, name").execute()
        classes = res.data or []
        print(f"Liczba klas SAMAR: {len(classes)}")

        # 2. Base RV & Depreciation (samar_class_depreciation_rates)
        res_depr = (
            supabase.table("samar_class_depreciation_rates")
            .select("samar_class_id, fuel_type_id, year")
            .execute()
        )
        depr = res_depr.data or []
        print(f"Wpisy w deprecjacji: {len(depr)}")

        # Sprawdź pokrycie bazowe dla każdej klasy
        class_ids = [c["id"] for c in classes]
        depr_class_ids = set(d["samar_class_id"] for d in depr)
        missing_depr = [c for c in classes if c["id"] not in depr_class_ids]
        print(f"Klasy bez przypisanej deprecjacji: {len(missing_depr)}")
        if missing_depr:
            print(f"  Przykłady: {[c['name'] for c in missing_depr[:5]]}")

        # 3. Mileage (samar_class_mileage_corrections)
        res_mil = (
            supabase.table("samar_class_mileage_corrections")
            .select("samar_class_id")
            .execute()
        )
        mil = res_mil.data or []
        mil_class_ids = set(m["samar_class_id"] for m in mil)
        missing_mil = [c for c in classes if c["id"] not in mil_class_ids]
        print(f"Klasy bez korekt przebiegu: {len(missing_mil)}")

        # 4. Brand corrections (ltr_admin_korekta_wr_markas)
        res_brand = supabase.table("ltr_admin_korekta_wr_markas").select("id").execute()
        print(f"Korekty marek: {len(res_brand.data or [])}")

        # 5. Paint types (paint_types)
        res_paint = (
            supabase.table("paint_types").select("id, name, wr_correction").execute()
        )
        print(f"Korekty lakieru (paint_types): {len(res_paint.data or [])}")

        # 6. Body types (body_type_wr_corrections)
        res_body = supabase.table("body_type_wr_corrections").select("id").execute()
        print(f"Korekty nadwozia: {len(res_body.data or [])}")

        # 7. Zabudowa (zabudowa_wr_corrections)
        res_zab = supabase.table("zabudowa_wr_corrections").select("id").execute()
        print(f"Korekty zabudowy: {len(res_zab.data or [])}")

        # 8. Rocznik (ltr_admin_korekta_wr_roczniks)
        res_rocznik = (
            supabase.table("ltr_admin_korekta_wr_roczniks").select("id").execute()
        )
        print(f"Korekty rocznika: {len(res_rocznik.data or [])}")

    except Exception as e:
        print(f"Błąd: {e}")


if __name__ == "__main__":
    asyncio.run(check_data())
