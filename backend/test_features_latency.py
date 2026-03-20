import time


def test_latency():
    from core.database import supabase
    from api.features_routes import get_vehicle_feature_state

    res = supabase.table("vehicle_synthesis").select("id").limit(1).execute()
    if not res.data:
        print("No vehicles found.")
        return

    vehicle_id = res.data[0]["id"]
    print(f"Testing vehicle ID: {vehicle_id}")

    # Run once to warm up connection
    get_vehicle_feature_state(vehicle_id)

    start_time = time.time()

    res_state = get_vehicle_feature_state(vehicle_id)

    end_time = time.time()

    print(f"Latency: {(end_time - start_time) * 1000:.2f} ms")
    print(f"Categories count: {len(res_state.get('categories', {}))}")
    print(f"Total features: {res_state.get('total_features', 0)}")


if __name__ == "__main__":
    test_latency()
