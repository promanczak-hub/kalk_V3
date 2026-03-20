from core.database import supabase


def test_leon():
    # Find Leon catalog
    res_cat = (
        supabase.schema("reverse_search")
        .table("model_document_sources")
        .select("id, brand, model_family, display_name")
        .ilike("model_family", "%leon%")
        .execute()
    )
    print("Leon Catalogs:", res_cat.data)

    # Find Leon vehicle
    res_veh = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, verification_status")
        .ilike("model", "%leon%")
        .execute()
    )
    print("Leon Vehicles:", res_veh.data)

    if res_veh.data:
        v_id = res_veh.data[0]["id"]
        # Check if there is any evidence
        res_ev = (
            supabase.schema("reverse_search")
            .table("vehicle_feature_evidence")
            .select("count")
            .eq("source_vehicle_id", v_id)
            .execute()
        )
        print(f"Evidence count for vehicle {v_id}:", res_ev.count)


if __name__ == "__main__":
    test_leon()
