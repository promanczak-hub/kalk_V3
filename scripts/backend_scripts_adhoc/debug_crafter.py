from core.database import supabase


def main():
    # Znajdźmy Crafter Furgon
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model")
        .eq("model", "Crafter")
        .execute()
    )
    for row in res.data:
        vid = row["id"]
        print(f"Pojazd: {row['brand']} {row['model']} (ID: {vid})")
        # Sprawdź matrix cache
        cache_res = (
            supabase.table("vehicle_matrix_cache")
            .select("margin_pct, kalkulacja_id, count(*)")
            .eq("vehicle_id", vid)
            .execute()
        )
        print(f" Cache: {len(cache_res.data)} rekordów.")
        if cache_res.data:
            print(" Pierwszy rekord z brzegu:", cache_res.data[0])


if __name__ == "__main__":
    main()
