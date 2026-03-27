from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase


def main():
    payload = {
        "samar_class_id": 26,
        "fuel_type_id": 4,
        "year_0": 0.35,
        "year_1": 0.38,
        "year_2": 0.41,
        "year_3": 0.44,
        "year_4": 0.47,
        "year_5": 0.50,
        "year_6": 0.53,
        "year_7": 0.56,
    }

    try:
        check = (
            supabase.table("tab_okres_final")
            .select("id")
            .eq("samar_class_id", 26)
            .eq("fuel_type_id", 4)
            .execute()
        )
        if check.data:
            supabase.table("tab_okres_final").update(payload).eq(
                "id", check.data[0]["id"]
            ).execute()
            print("OK, updated")
        else:
            supabase.table("tab_okres_final").insert(payload).execute()
            print("OK, inserted")
    except Exception as e:
        if hasattr(e, "json"):
            print("ERROR JSON:", e.json())
        elif hasattr(e, "details"):
            print("ERROR DETAILS:", getattr(e, "details"))
        elif hasattr(e, "message"):
            print("ERROR MESSAGE:", getattr(e, "message"))
        else:
            print("ERROR STR:", str(e))


if __name__ == "__main__":
    main()
