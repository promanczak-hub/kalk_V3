from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase


def main():
    # Szukamy jakiejkolwiek klasy ze stawkami dla silnika Diesel (id 2)
    resp = (
        supabase.table("tab_okres_final")
        .select("*")
        .eq("fuel_type_id", 2)
        .limit(1)
        .execute()
    )
    if resp.data:
        template = resp.data[0]
        print(
            f"Znaleziono szablon silnika Diesel z klasy: {template['samar_class_id']}"
        )

        payload = {
            "samar_class_id": 26,
            "fuel_type_id": 2,  # Diesel (ON)
            "year_0": template.get("year_0", 0.0),
            "year_1": template.get("year_1", 0.0),
            "year_2": template.get("year_2", 0.0),
            "year_3": template.get("year_3", 0.0),
            "year_4": template.get("year_4", 0.0),
            "year_5": template.get("year_5", 0.0),
            "year_6": template.get("year_6", 0.0),
            "year_7": template.get("year_7", 0.0),
        }

        try:
            supabase.table("tab_okres_final").insert(payload).execute()
            print("Zapisano klasę 26 Diesel (ON) pomyślnie z szablonu!")
        except Exception as e:
            if hasattr(e, "json"):
                print("Błąd zapisu:", e.json())
            else:
                print("Błąd:", e)
    else:
        print(
            "Nie znaleziono w ogóle żadnej innej klasy Diesel! (Pusta baza dla diesla?)"
        )


if __name__ == "__main__":
    main()
