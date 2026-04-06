from core.database import supabase


def main():
    try:
        res = (
            supabase.table("vehicle_synthesis")
            .select("id, synthesis_data")
            .ilike("synthesis_data->>brand", "%Skoda%")
            .ilike("synthesis_data->>model", "%Fabia%")
            .execute()
        )
        fabia_ids = [row["id"] for row in res.data]
        print(f"Znalazlem {len(fabia_ids)} Fabii.")

        jobs_res = (
            supabase.table("calculation_jobs")
            .select("*")
            .in_("vehicle_id", fabia_ids)
            .execute()
        )
        for j in jobs_res.data:
            vid = j.get("vehicle_id")
            s = j.get("status")
            ec = j.get("error_code")
            ed = j.get("error_detail")
            print(f"Vehicle {vid} -> Status: {s}, Error: {ec} ({ed})")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
