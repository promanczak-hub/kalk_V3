import json
import os
from core.samar_mapper import map_to_samar_class


def test_mapper():
    with open("d:/kalk_v3/backend/online_bmw_x3_rest2.json", encoding="utf-8") as f:
        data = json.load(f)

    for i, x3 in enumerate(data):
        print(f"--- BMW {i + 1} ---")
        ai_data = x3.get("mapped_ai_data", {})
        card = x3.get("card_summary", {})

        # Odtworzenie parametrów przekazywanych z parsera do mappera w pipeline
        # Zgodnie z main_pipeline lub background workers dla BMW:
        brand = ai_data.get("brand") or card.get("brand") or "BMW"
        model = ai_data.get("model") or card.get("model") or "X3"

        # the synthesis process puts trim_level from ai_data or card
        trim = (
            ai_data.get("trim_level")
            or card.get("trim_level")
            or card.get("powertrain")
        )

        body = card.get("body_style") or ai_data.get("vehicle_type")
        trans = ai_data.get("transmission") or card.get("transmission")
        seats = card.get("number_of_seats")

        try:
            seats = int(seats) if seats else None
        except:
            seats = None

        print("Wejściowe:")
        print(f"Brand: {brand}, Model: {model}, Trim: {trim}")
        print(f"Body: {body}, Trans: {trans}, Seats: {seats}")

        class_name, candidates = map_to_samar_class(
            brand=brand,
            model=model,
            trim=trim,
            body_style=body,
            transmission=trans,
            number_of_seats=seats,
        )
        print(f"Wynik mappy: {class_name}")
        for c in candidates:
            print(f" - {c['klasa']} ({c['confidence']:.2f})")


if __name__ == "__main__":
    os.environ["VITE_SUPABASE_URL"] = "https://gnpsdiarmwvqhqbyetce.supabase.co"
    os.environ["VITE_SUPABASE_ANON_KEY"] = (
        "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"
    )
    test_mapper()
