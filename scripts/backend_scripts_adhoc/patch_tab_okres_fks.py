"""
Patchuje tab_okres_final: ustawia poprawne samar_class_id i fuel_type_id
na podstawie stringow samar_class i engine_type.
"""

from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase

# Mapowanie z stringów tab_okres_final → samar_class_id (z tabeli samar_classes)
SAMAR_CLASS_MAP: dict[str, int] = {
    "Podstawowa - A MINI": 1,
    "Podstawowa - B MAŁE": 2,
    "Podstawowa - C NIŻSZA ŚREDNIA": 3,
    "Podstawowa - D ŚREDNIA": 4,
    "Podstawowa - E WYŻSZA": 5,
    "Podstawowa - F LUKSUSOWE": 6,
    "Podstawowa - G SUPER LUKSUSOWE": 7,
    "Sportowo-rekreacyjne - A MINI": 12,
    "Sportowo-rekreacyjne - B MAŁE": 13,
    "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA": 16,
    "Sportowo-rekreacyjne - D ŚREDNIA": 19,
    "Sportowo-rekreacyjne - E WYŻSZA": 23,  # Fsport
    "Sportowo-rekreacyjne - F LUKSUSOWE": 23,
    "Sportowo-rekreacyjne - G SUPER LUKSUSOWE": 23,
    "Terenowo-rekreacyjne (SUV) - B MAŁE": 14,
    "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA": 17,
    "Terenowo-rekreacyjne (SUV) - D ŚREDNIA": 20,
    "Terenowo-rekreacyjne (SUV) - E WYŻSZA": 22,  # Esuv
    "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE": 24,
    "Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE": 24,
    "Vany - B MICROVANY": 15,
    "Vany - C MINIVANY": 18,
    "Vany - D VANY": 21,
    "Vany - E WYŻSZA": 21,
    "Vany - F LUKSUSOWE": 21,
    "Kombivany - H KOMBI-VANY": 26,  # Mvan
    "Lekkie dostawcze - KOMBI VAN": 26,
    "Lekkie dostawcze - VAN": 26,
    "Średnie dostawcze - ŚREDNIE DOSTAWCZE": 26,
    "Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE": 26,
    "Minibusy - I MINIBUSY": 25,
    "Autobusy - AUTOBUSY": 25,
    "Pick-up - PICK-UP": 29,
}

# Mapowanie z engine_type strings → fuel_type_id
ENGINE_MAP: dict[str, int] = {
    "Benzyna (PB)": 1,
    "Benzyna mHEV (PB-mHEV)": 3,
    "Diesel (ON)": 2,
    "Diesel mHEV (ON-mHEV)": 4,
    "Elektryczny (BEV)": 7,
    "Hybryda (HEV)": 5,
    "LPG": 9,
    "Plug-in Hybrid (PHEV)": 6,
    "Wodór (FCEV)": 8,
}


def main() -> None:
    res = (
        supabase.table("tab_okres_final")
        .select("id, samar_class, engine_type")
        .execute()
    )
    rows = res.data
    print(f"Found {len(rows)} rows in tab_okres_final")

    success = 0
    skipped = 0

    for row in rows:
        sc = str(row.get("samar_class", "")).strip()
        eng = str(row.get("engine_type", "")).strip()
        row_id = row["id"]

        c_id = SAMAR_CLASS_MAP.get(sc)
        f_id = ENGINE_MAP.get(eng)

        if c_id and f_id:
            try:
                supabase.table("tab_okres_final").update(
                    {"samar_class_id": c_id, "fuel_type_id": f_id}
                ).eq("id", row_id).execute()
                success += 1
            except Exception as e:
                print(f"Error updating {sc}/{eng}: {getattr(e, 'message', str(e))}")
        else:
            skipped += 1
            if skipped <= 5:
                print(f"  Unmapped: '{sc}' / '{eng}' (c_id={c_id}, f_id={f_id})")

    print(f"\nDone: {success} updated, {skipped} skipped.")


if __name__ == "__main__":
    main()
