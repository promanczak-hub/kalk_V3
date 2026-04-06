import json
from dotenv import load_dotenv

# Set PYTHONPATH and run from backend root
load_dotenv()
load_dotenv("../frontend/.env.local")

from core.extractor_v2 import extract_vehicle_data_v2
from core.json_utils import clean_json_response
from services.ai_mapper_service import map_vehicle_data_flash
from core.samar_mapper import map_to_samar_class


def main():
    pdf_path = r"C:\Users\proma\Downloads\Crafter-Furgon_2703_SGRE.pdf"

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    from core.document_converter import convert_to_gemini_input

    gemini_data, gemini_mime = convert_to_gemini_input(file_bytes, "application/pdf")

    print("Sending to Gemini for extraction...")
    json_response = extract_vehicle_data_v2(
        gemini_data, mime_type=gemini_mime, on_progress=lambda x: print("Progress:", x)
    )

    cleaned_json = clean_json_response(json_response)
    parsed_data = json.loads(cleaned_json)

    print("\n--- EXTRACTED DATA ---")
    print(json.dumps(parsed_data.get("card_summary", {}), indent=2))

    print("\n--- MAPPING ---")
    mapped_data = map_vehicle_data_flash(parsed_data)
    print(json.dumps(mapped_data, indent=2))

    brand = parsed_data.get("brand") or mapped_data.get("brand")
    model = parsed_data.get("model") or mapped_data.get("model")

    card_summary = parsed_data.get("card_summary", {})
    segment = card_summary.get("segment") or card_summary.get("car_segment")
    body_style = card_summary.get("body_style")
    transmission = mapped_data.get("transmission")
    seats_raw = card_summary.get("number_of_seats")
    trim = mapped_data.get("trim_level")

    samar_name, samar_candidates = map_to_samar_class(
        brand=brand,
        model=model,
        segment=segment,
        body_style=body_style,
        trim=trim,
        transmission=transmission,
        number_of_seats=int(seats_raw) if seats_raw else None,
    )

    print("\n--- SAMAR CLASS ---")
    print(f"Name: {samar_name}")
    print(f"Candidates: {samar_candidates}")


if __name__ == "__main__":
    main()
