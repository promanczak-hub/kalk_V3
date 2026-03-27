from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase


def main():
    # 1. Popraw cost_tyre_storage: 216 PLN/rok
    res = (
        supabase.table("tyre_configurations")
        .update({"config_value": "216"})
        .eq("config_key", "cost_tyre_storage")
        .execute()
    )
    print("cost_tyre_storage updated:", res.data)

    # 2. Zmien klasę SAMAR dla Škoda Superb (GOC-23-150658) na "Podstawowa - D ŚREDNIA"
    # samar_class_id=4 = "Podstawowa - D ŚREDNIA" (z CLASS_MAP)
    res2 = (
        supabase.table("vehicle_data")
        .update({"samar_class_id": 4})
        .eq("offer_number", "GOC-23-150658")
        .execute()
    )
    print("Skoda Superb samar_class_id updated:", res2.data)


if __name__ == "__main__":
    main()
