import os
import sys

from dotenv import load_dotenv

# Add backend to path
backend_dir = os.path.join(os.getcwd(), "backend")
sys.path.append(backend_dir)

# Load env
load_dotenv(os.path.join(backend_dir, ".env"))

# engine_mapper uses these specific names
os.environ["VITE_SUPABASE_URL"] = os.environ.get("SUPABASE_URL", "")
os.environ["VITE_SUPABASE_ANON_KEY"] = os.environ.get("SUPABASE_KEY", "")

from core.engine_mapper import map_to_engine_class
from services.ai_mapper_service import map_vehicle_data_flash

# Data from vehicle 90c7e6d6-718f-4b8a-9fc8-eac92bb6510f synthesis_data
mock_original_json = {
    "brand": "SKODA",
    "model": "Superb Drive",
    "powertrain": "1.5 TSI mHEV 110 kW (150 KM) DSG",
    "fuel": "Benzyna",
    "transmission": "Automatyczna, 7-biegowa",
    "configuration_code": "CD6MDVS9",
    "power_hp": 150,
    "power_kw": 110,
    "engine_designation": "TSI",
    "card_summary": {
        "powertrain": {"engine_designation": "TSI", "engine_capacity": "1.5"},
        "power_hp": 150,
    },
}


def test_engine_mapper():
    print("\n--- Testing core.engine_mapper.map_to_engine_class ---")
    best_name, best_category, candidates = map_to_engine_class(
        fuel=mock_original_json["fuel"],
        engine_designation=mock_original_json["engine_designation"],
        power=f"{mock_original_json['power_hp']} KM",
        model=mock_original_json["model"],
    )
    print(f"Best Match: {best_name} ({best_category})")
    print("Candidates:")
    for c in candidates[:3]:
        print(f"  - {c['klasa']}: {c['confidence']}")


def test_remap_guard_simulation():
    print("\n--- Testing Guard Simulation (as in extract_routes.py) ---")
    # Simulate Step 1 (Flash mapper)
    mapped_data = map_vehicle_data_flash(mock_original_json)
    previous_fuel = mapped_data.get("fuel", "")
    print(f"Initial AI Fuel: {previous_fuel}")

    # Simulate Step 2 (Engine classification)
    powertrain_data = mock_original_json.get("card_summary", {}).get("powertrain", {})
    eng_name, eng_cat, eng_candidates = map_to_engine_class(
        fuel=previous_fuel,
        engine_designation=powertrain_data.get("engine_designation"),
        power=str(mock_original_json.get("power_hp")),
        capacity=str(powertrain_data.get("engine_capacity")),
        model=mock_original_json.get("model"),
    )
    print(f"Engine Mapper Suggestion: {eng_name}")

    # Apply Guard Logic
    is_mhev_previously = "mHEV" in previous_fuel
    is_new_mhev = "mHEV" in eng_name
    is_generic_new = eng_name in ["Benzyna (PB)", "Diesel (ON)", "LPG"]

    final_fuel = previous_fuel
    if eng_name != "UNKNOWN":
        if is_mhev_previously and is_generic_new and not is_new_mhev:
            print(f"GUARD TRIGGERED: Preserving '{previous_fuel}' over '{eng_name}'")
            final_fuel = previous_fuel
        else:
            print(f"GUARD PASSED: Using '{eng_name}'")
            final_fuel = eng_name

    print(f"FINAL FUEL: {final_fuel}")
    success = "mHEV" in final_fuel
    print(f"VERDICT: {'SUCCESS' if success else 'FAILURE'}")


if __name__ == "__main__":
    with open("backend/debug_engine_mapping_output.txt", "w", encoding="utf-8") as f:
        import sys

        original_stdout = sys.stdout
        sys.stdout = f
        try:
            test_engine_mapper()
            test_remap_guard_simulation()
        finally:
            sys.stdout = original_stdout
    print("Results written to backend/debug_engine_mapping_output.txt")
