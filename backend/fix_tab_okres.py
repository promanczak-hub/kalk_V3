from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase


def main():
    # Pobieramy istniejcy samar_class_id = 26 z old table
    resp = (
        supabase.table("samar_class_depreciation_rates")
        .select("*")
        .eq("samar_class_id", 26)
        .execute()
    )

    if not resp.data:
        print("Nie ma danych w ogole dla klasy 26!")
        return

    # Gromadzimy per fuel
    fuel_data = {}
    for row in resp.data:
        fuel_id = row["fuel_type_id"]
        year = int(row["year"])
        base = float(row.get("base_depreciation_percent", 0.0) or 0.0)

        if fuel_id not in fuel_data:
            fuel_data[fuel_id] = {
                "samar_class_id": 26,
                "fuel_type_id": fuel_id,
            }
            for y in range(8):
                fuel_data[fuel_id][f"year_{y}"] = 0.0

        fuel_data[fuel_id][f"year_{year}"] = base

    try:
        # Wstawiamy do tab_okres_final
        for fuel_id, payload in fuel_data.items():
            print(
                f"Update tab_okres_final dla class {payload['samar_class_id']}, fuel {fuel_id}..."
            )

            # Check if exists
            check = (
                supabase.table("tab_okres_final")
                .select("id")
                .eq("samar_class_id", payload["samar_class_id"])
                .eq("fuel_type_id", fuel_id)
                .execute()
            )
            if check.data:
                print("Row exists. Updating.")
                supabase.table("tab_okres_final").update(payload).eq(
                    "id", check.data[0]["id"]
                ).execute()
            else:
                print("Row missing. Inserting.")
                supabase.table("tab_okres_final").insert(payload).execute()

        print("Done")
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Server response: {getattr(e, 'message', str(e))}")


if __name__ == "__main__":
    main()
