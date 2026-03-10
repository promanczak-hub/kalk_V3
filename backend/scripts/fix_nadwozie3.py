from backend.core.database import supabase


def fix_nadwozie2():
    body_types = [
        # Osobowe
        ("Osobowe - Hatchback", ""),
        ("Osobowe - Sedan", ""),
        ("Osobowe - Kombi", ""),
        ("Osobowe - Liftback", ""),
        ("Osobowe - SUV", ""),
        ("Osobowe - Crossover", ""),
        ("Osobowe - Coupe", ""),
        ("Osobowe - Cabrio", ""),
        ("Osobowe - Minivan", ""),
        ("Osobowe - Pick-up", ""),
        ("Osobowe - Wieloosobowy", ""),
        # Dostawcze
        ("Dostawcze - Furgon", ""),
        ("Dostawcze - Skrzyniowy", 0.04),
        ("Dostawcze - Kontener", 0.04),
        ("Dostawcze - Chłodnia / Izoterma", 0.04),
        ("Dostawcze - Pick-up", 0.04),
        ("Dostawcze - Wieloosobowy / Brygadowy", 0.04),
        ("Dostawcze - Laweta", 0.04),
        ("Dostawcze - Wywrotka", 0.04),
    ]
    new_nadwozie = [
        {"id": i + 1, "col_1": bt, "col_2": val}
        for i, (bt, val) in enumerate(body_types)
    ]

    update_res = (
        supabase.table("excel_drafts")
        .update({"data_rows": new_nadwozie})
        .eq("sheet_name", "NADWOZIE")
        .execute()
    )
    print(
        "Zaktualizowano wiersze NADWOZIE z wartością 4% dla nadwozi specjalnych:",
        len(new_nadwozie),
        "elementów",
    )


if __name__ == "__main__":
    fix_nadwozie2()
