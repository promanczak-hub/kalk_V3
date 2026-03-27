from core.database import supabase


def main():
    try:
        res = (
            supabase.table("vehicle_synthesis")
            .select("id, synthesis_data")
            .ilike("synthesis_data->>brand", "%Skoda%")
            .ilike("synthesis_data->>model", "%Fabia%")
            .limit(5)
            .execute()
        )
        for row in res.data:
            vid = row["id"]
            brand = (
                row["synthesis_data"]
                .get("mapped_ai_data", {})
                .get("brand", row["synthesis_data"].get("brand", ""))
            )
            model = (
                row["synthesis_data"]
                .get("mapped_ai_data", {})
                .get("model", row["synthesis_data"].get("model", ""))
            )
            print(f"Vehicle: {brand} {model} (ID: {vid})")
            try:
                kalk_res = (
                    supabase.table("ltr_kalkulacje")
                    .select("id, matrix_cache")
                    .eq("stan_json->>vehicle_id", vid)
                    .execute()
                )
                for k in kalk_res.data:
                    cache = k.get("matrix_cache") or {}
                    print(f"  Kalkulacja {k['id']} ma {len(cache)} wariantow.")
                    variants = list(cache.keys())
                    print(f"  Przykladowe klucze: {variants[:10]}")
            except Exception as e:
                if hasattr(e, "details"):
                    print(f"  Error Kalkulacje: {e.details} | {e.message}")
                else:
                    print(f"  Error Kalkulacje: {e}")
    except Exception as e:
        print(f"Error Vehicle: {e}")


if __name__ == "__main__":
    main()
