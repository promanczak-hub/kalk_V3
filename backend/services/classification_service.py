from typing import Dict, Any
from core.database import supabase as supabase_client
from services.ai_mapper_service import map_vehicle_data_flash
from core.samar_mapper import map_to_samar_class
from core.engine_mapper import map_to_engine_class


def run_full_classification_pipeline(original_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full classification pipeline: Flash mapper → Engine → SAMAR.
    Returns mapped_ai_data with samar_category, engine_class, candidates.
    """
    print("[REMAP] Running full classification pipeline (Service)...")

    # Step 1: Flash mapper (brand, model, fuel, transmission, vehicle_type)
    mapped_data = map_vehicle_data_flash(original_json)

    card_summary = original_json.get("card_summary", {})
    brand = mapped_data.get("brand") or original_json.get("brand")
    model = mapped_data.get("model") or original_json.get("model")
    trim = mapped_data.get("trim_level")

    # Step 2: Engine classification (first — doesn't depend on SAMAR)
    powertrain_data = (
        card_summary.get("powertrain", {})
        if isinstance(card_summary.get("powertrain"), dict)
        else {}
    )
    engine_designation = powertrain_data.get("engine_designation")
    capacity = powertrain_data.get("engine_capacity")
    power = card_summary.get("power_hp")

    eng_name, eng_cat, eng_candidates = map_to_engine_class(
        fuel=mapped_data.get("fuel"),
        engine_designation=engine_designation,
        power=str(power) if power else None,
        capacity=str(capacity) if capacity else None,
        model=model,
        trim=trim,
    )

    previous_fuel = mapped_data.get("fuel", "")
    is_mhev_previously = "mHEV" in previous_fuel

    if eng_name != "UNKNOWN":
        # Guard: If previously identified as mHEV, don't downgrade to generic Petrol/Diesel
        # unless the new identification is also mHEV or clearly superior (not generic)
        is_new_mhev = "mHEV" in eng_name
        is_generic_new = eng_name in ["Benzyna (PB)", "Diesel (ON)", "LPG"]

        if is_mhev_previously and is_generic_new and not is_new_mhev:
            print(
                f"[REMAP] Guard: Preserving mHEV status '{previous_fuel}' over generic '{eng_name}'"
            )
        else:
            mapped_data["fuel"] = eng_name
            mapped_data["engine_class"] = eng_cat
            mapped_data["engine_candidates"] = eng_candidates
    elif mapped_data.get("fuel"):
        try:
            engines_resp = (
                supabase_client.table("engines")
                .select("category")
                .eq("name", mapped_data.get("fuel"))
                .execute()
            )
            if engines_resp.data:
                mapped_data["engine_class"] = engines_resp.data[0]["category"]
        except Exception as db_e:
            print(f"[REMAP] Engine fallback DB error: {db_e}")

    # Step 3: SAMAR classification (last — uses full context incl. seats)
    segment = card_summary.get("segment") or card_summary.get("car_segment")
    body_style = card_summary.get("body_style")
    transmission = mapped_data.get("transmission")
    seats_raw = card_summary.get("number_of_seats")

    samar_name, samar_candidates = map_to_samar_class(
        brand=brand,
        model=model,
        segment=segment,
        body_style=body_style,
        trim=trim,
        transmission=transmission,
        number_of_seats=int(seats_raw) if seats_raw else None,
    )
    mapped_data["samar_category"] = samar_name
    mapped_data["samar_candidates"] = samar_candidates

    print(f"[REMAP] Done: Engine={eng_name}/{eng_cat}, SAMAR={samar_name}")
    return mapped_data
