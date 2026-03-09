import json
from backend.core.database import supabase


def fix_nadwozie():
    body_types = [
        # Osobowe
        "Osobowe - Hatchback",
        "Osobowe - Sedan",
        "Osobowe - Kombi",
        "Osobowe - Liftback",
        "Osobowe - SUV",
        "Osobowe - Crossover",
        "Osobowe - Coupe",
        "Osobowe - Cabrio",
        "Osobowe - Minivan",
        "Osobowe - Pick-up",
        "Osobowe - Wieloosobowy",
        # Dostawcze
        "Dostawcze - Furgon",
        "Dostawcze - Skrzyniowy",
        "Dostawcze - Kontener",
        "Dostawcze - Chłodnia / Izoterma",
        "Dostawcze - Pick-up",
        "Dostawcze - Wieloosobowy / Brygadowy",
        "Dostawcze - Laweta",
        "Dostawcze - Wywrotka",
    ]
    new_nadwozie = [
        {"id": i + 1, "col_1": bt, "col_2": ""} for i, bt in enumerate(body_types)
    ]

    update_res = (
        supabase.table("excel_drafts")
        .update({"data_rows": new_nadwozie})
        .eq("sheet_name", "NADWOZIE")
        .execute()
    )
    print("Zaktualizowano wiersze NADWOZIE:", len(new_nadwozie), "elementów")


if __name__ == "__main__":
    fix_nadwozie()
