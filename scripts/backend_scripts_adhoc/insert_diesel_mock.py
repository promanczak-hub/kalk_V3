from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase


def main():
    payload = {
        "samar_class_id": 26,
        "fuel_type_id": 2,  # Diesel (ON)
        "year_0": 0.30,
        "year_1": 0.40,
        "year_2": 0.50,
        "year_3": 0.60,
        "year_4": 0.70,
        "year_5": 0.80,
        "year_6": 0.85,
        "year_7": 0.90,
    }

    try:
        supabase.table("tab_okres_final").insert(payload).execute()
        print("Zapisano mock dla klasy 26 Diesel (ON) pomyślnie!")
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Error Message: {getattr(e, 'message', str(e))}")


if __name__ == "__main__":
    main()
