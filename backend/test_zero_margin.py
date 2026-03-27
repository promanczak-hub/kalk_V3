from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles


def main():
    # Znajdź jedno auto
    res = supabase.table("vehicle_synthesis").select("id").limit(1).execute()
    if not res.data:
        print("Brak aut do testu.")
        return
    vid = res.data[0]["id"]
    print(f"Test dla pojazdu: {vid}")

    # Uruchom synchronicznie odświeżanie cache (worker function)
    refresh_matrix_cache_for_vehicles([vid])
    print("Refresh wykonany.")

    # Odpytaj o utworzone wpisy w cache
    cache_res = (
        supabase.table("vehicle_matrix_cache")
        .select("margin_pct, monthly_price_net")
        .eq("vehicle_id", vid)
        .limit(5)
        .execute()
    )
    print("Przykładowe rekordy pobrane z cache:")
    for row in cache_res.data:
        print(row)


if __name__ == "__main__":
    main()
