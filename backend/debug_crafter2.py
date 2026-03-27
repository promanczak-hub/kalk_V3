from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles


def main():
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model")
        .ilike("brand", "%Volkswagen%")
        .execute()
    )
    for row in res.data:
        if "Crafter" in row["model"] or "Caddy" in row["model"]:
            vid = row["id"]
            print(f"Pojazd: {row['brand']} {row['model']} (ID: {vid})")
            cache_res = (
                supabase.table("vehicle_matrix_cache")
                .select("kalkulacja_id")
                .eq("vehicle_id", vid)
                .limit(1)
                .execute()
            )
            print(f" Cache rows: {'Yes' if cache_res.data else 'No'}")

            # Let's see if we can refresh it right now
            if "Crafter" in row["model"]:
                print("Próbuję wygenerować matrix dla Craftera...")
                try:
                    refresh_matrix_cache_for_vehicles([vid])
                    print("Refresh success.")
                except Exception as e:
                    print(f"Refresh failed: {e}")
            print("---")


if __name__ == "__main__":
    main()
