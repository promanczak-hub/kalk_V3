from backend.core.database import supabase


def fix_drafts2():
    # 2. ROCZNIK
    new_rocznik = [
        {"id": 1, "col_1": "Bieżący", "col_2": 0.0},
        {"id": 2, "col_1": "Bieżący-1", "col_2": -0.08},
    ]
    supabase.table("excel_drafts").update({"data_rows": new_rocznik}).eq(
        "sheet_name", "ROCZNIK"
    ).execute()
    print("Zaktualizowano wiersze ROCZNIK")

    # 3. NADWOZIE
    # Zgodnie z poleceniem: podziały na osobowe i dostawcze
    body_types = [
        "Osobowe - Hatchback",
        "Osobowe - Sedan",
        "Osobowe - Kombi",
        "Osobowe - SUV",
        "Osobowe - Coupe",
        "Osobowe - Cabrio",
        "Osobowe - Van",
        "Osobowe - Minivan",
        "Dostawcze - Pick-up",
        "Dostawcze - Furgon",
        "Dostawcze - Skrzynia",
        "Dostawcze - Minibus",
        "Dostawcze - Kontener",
    ]
    new_nadwozie = [
        {"id": i + 1, "col_1": bt, "col_2": ""} for i, bt in enumerate(body_types)
    ]
    supabase.table("excel_drafts").update({"data_rows": new_nadwozie}).eq(
        "sheet_name", "NADWOZIE"
    ).execute()
    print("Zaktualizowano wiersze NADWOZIE")


if __name__ == "__main__":
    fix_drafts2()
