from core.database import supabase


def fix_drafts():
    # 1. KOLOR
    new_kolor = [
        {"id": 1, "col_1": "Metalik", "col_2": ""},
        {"id": 2, "col_1": "Niemetalik", "col_2": "-1%"},
    ]
    supabase.table("excel_drafts").update({"data_rows": new_kolor}).eq(
        "sheet_name", "KOLOR"
    ).execute()
    print("Zaktualizowano wiersze KOLOR")

    # 2. ROCZNIK
    new_rocznik = [
        {"id": 1, "col_1": "Bieżący", "col_2": ""},
        {"id": 2, "col_1": "Bieżący-1", "col_2": ""},
    ]
    supabase.table("excel_drafts").update({"data_rows": new_rocznik}).eq(
        "sheet_name", "ROCZNIK"
    ).execute()
    print("Zaktualizowano wiersze ROCZNIK")

    # 3. NADWOZIE
    body_types = [
        "Hatchback",
        "Sedan",
        "Kombi",
        "SUV",
        "Coupe",
        "Cabrio",
        "Van",
        "Minivan",
        "Pick-up",
    ]
    new_nadwozie = [
        {"id": i + 1, "col_1": bt, "col_2": ""} for i, bt in enumerate(body_types)
    ]
    supabase.table("excel_drafts").update({"data_rows": new_nadwozie}).eq(
        "sheet_name", "NADWOZIE"
    ).execute()
    print("Zaktualizowano wiersze NADWOZIE")


if __name__ == "__main__":
    fix_drafts()
