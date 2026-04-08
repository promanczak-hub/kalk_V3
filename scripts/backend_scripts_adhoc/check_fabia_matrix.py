from core.database import supabase


def main():
    res = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
    fabias = []
    for v in res.data:
        import json

        sd_str = json.dumps(v.get("synthesis_data", {}))
        if "Skoda" in sd_str and "Fabia" in sd_str:
            fabias.append(v["id"])

    print(f"Fabias: {fabias}")

    matrix = (
        supabase.table("vehicle_matrix_cache")
        .select("vehicle_id")
        .in_("vehicle_id", fabias)
        .execute()
    )
    counts = {}
    for row in matrix.data:
        counts[row["vehicle_id"]] = counts.get(row["vehicle_id"], 0) + 1

    print("Matrix variants count per Fabia:")
    for v_id in fabias:
        print(f" {v_id}: {counts.get(v_id, 0)} variants")


if __name__ == "__main__":
    main()
