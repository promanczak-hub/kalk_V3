from core.database import supabase

# INHERIT_MAP z seed_depreciation_rates.py
INHERIT_MAP = {
    3: 1,  # Benzyna mHEV ← Benzyna
    4: 2,  # Diesel mHEV  ← Diesel
    5: 1,  # Hybryda (HEV) ← Benzyna
    6: 1,  # PHEV ← Benzyna
    7: 1,  # BEV ← Benzyna (w ostateczności)
    8: 7,  # FCEV ← BEV
    9: 1,  # LPG ← Benzyna
}


def fix_mileage_corrections():
    print("Pobieram istniejące korekty...")
    res = supabase.table("samar_class_mileage_corrections").select("*").execute()
    existing_records = res.data

    # Tworzymy mapę (class_id, fuel_id) -> record
    record_map = {(r["samar_class_id"], r["fuel_type_id"]): r for r in existing_records}
    class_ids = set(r["samar_class_id"] for r in existing_records)

    inserts = []

    for c_id in class_ids:
        # Sprawdzamy dla każdego fuel_id od 1 do 9
        for fuel_id in range(1, 10):
            if (c_id, fuel_id) not in record_map:
                # Szukamy źródła do dziedziczenia
                source_fuel = INHERIT_MAP.get(fuel_id)
                if not source_fuel:
                    source_fuel = 1  # Fallback do benzyny

                source_record = record_map.get((c_id, source_fuel))

                # Jeśli źródła nadal nie ma, próbujemy jakiegokolwiek byle odziedziczyć klasę
                if not source_record:
                    any_record_for_class = [
                        r for r in existing_records if r["samar_class_id"] == c_id
                    ]
                    if any_record_for_class:
                        source_record = any_record_for_class[0]

                if source_record:
                    inserts.append(
                        {
                            "samar_class_id": c_id,
                            "fuel_type_id": fuel_id,
                            "under_threshold_percent": source_record[
                                "under_threshold_percent"
                            ],
                            "over_threshold_percent": source_record[
                                "over_threshold_percent"
                            ],
                        }
                    )
                    record_map[(c_id, fuel_id)] = source_record  # update virtual map
                    print(
                        f"Brak (klasa {c_id}, paliwo {fuel_id}) -> Skopiowano z paliwa {source_record['fuel_type_id']}"
                    )

    if inserts:
        print(f"Wstawiam {len(inserts)} brakujących korekt przebiegu...")
        supabase.table("samar_class_mileage_corrections").upsert(inserts).execute()
        print("Gotowe. Skompletowano brakujące dane.")
    else:
        print("Nie znaleziono braków. Baza jest kompletna.")


if __name__ == "__main__":
    fix_mileage_corrections()
