"""Seed replacement_car_rates for the 28 new SAMAR classes (IDs 100-127).

Clears old data and inserts fresh rows with confirmed daily rates.
"""

from core.database import supabase

# Confirmed mapping: samar_class_id -> daily_rate_net (PLN)
NEW_RATES: dict[int, float] = {
    # Podstawowa (A-G)
    100: 50.0,  # A MINI
    101: 60.0,  # B MAŁE
    102: 70.0,  # C NIŻSZA ŚREDNIA
    103: 100.0,  # D ŚREDNIA
    104: 185.0,  # E WYŻSZA
    105: 250.0,  # F LUKSUSOWE
    106: 250.0,  # G SUPER LUKSUSOWE
    # Vany (B-F)
    107: 80.0,  # B MICROVANY
    108: 80.0,  # C MINIVANY
    109: 110.0,  # D VANY
    110: 110.0,  # E WYŻSZA
    111: 110.0,  # F LUKSUSOWE
    # Sportowo-rekreacyjne (A-G) – all 100
    112: 100.0,  # A MINI
    113: 100.0,  # B MAŁE
    114: 100.0,  # C NIŻSZA ŚREDNIA
    115: 100.0,  # D ŚREDNIA
    116: 100.0,  # E WYŻSZA
    117: 100.0,  # F LUKSUSOWE
    118: 100.0,  # G SUPER LUKSUSOWE
    # Terenowo-rekreacyjne / SUV (B-G) – all 100
    119: 100.0,  # B MAŁE
    120: 100.0,  # C NIŻSZA ŚREDNIA
    121: 100.0,  # D ŚREDNIA
    122: 100.0,  # E WYŻSZA
    123: 100.0,  # F LUKSUSOWE
    124: 100.0,  # G SUPER LUKSUSOWE
    # Specjalne
    125: 80.0,  # Kombivany - H
    126: 130.0,  # Minibusy - I
    127: 130.0,  # Kempingowe - K
}

AVERAGE_DAYS = 6.5


def seed() -> None:
    """Clear old rows and insert fresh rates for 28 classes."""
    classes_resp = (
        supabase.table("samar_classes").select("id, name").order("id").execute()
    )
    classes = classes_resp.data or []

    insert_rows: list[dict] = []
    for cls in classes:
        cid = cls["id"]
        if cid not in NEW_RATES:
            print(f"⚠️  Pomijam klasę {cid}: {cls['name']} (brak stawki)")
            continue
        insert_rows.append(
            {
                "samar_class_id": cid,
                "samar_class_name": cls["name"],
                "average_days_per_year": AVERAGE_DAYS,
                "daily_rate_net": NEW_RATES[cid],
            }
        )

    # Delete all existing rows
    supabase.table("replacement_car_rates").delete().gte("samar_class_id", 0).execute()
    print("🗑️  Wyczyszczono starą tabelę replacement_car_rates")

    if insert_rows:
        res = supabase.table("replacement_car_rates").insert(insert_rows).execute()
        print(f"✅ Zaseedowano {len(res.data)} wierszy")
    else:
        print("❌ Brak danych do seedowania")


if __name__ == "__main__":
    seed()
