import asyncio
import json
from core.extractor_v2 import extract_vehicle_data_v2
from dotenv import load_dotenv

load_dotenv()


async def main():
    file_path = r"C:\Users\proma\Downloads\oferta_goa-26-78454-30d37f (1).pdf"
    print(f"Reading file: {file_path}")

    with open(file_path, "rb") as f:
        file_content = f.read()

    mime_type = "application/pdf"

    print("Running extraction pipeline...")
    # Pass bytes directly
    result_str = extract_vehicle_data_v2(file_content, mime_type)
    result = json.loads(result_str)

    print("\n--- EXTRACTION RESULT ---")
    card_summary = result.get("card_summary", {})
    keys_to_print = [
        "base_price",
        "options_price",
        "total_price",
        "powertrain",
        "engine_power_hp",
        "fuel",
    ]
    print("CARD SUMMARY:")
    for k in keys_to_print:
        print(f"  {k}: {card_summary.get(k)}")

    dt = result.get("digital_twin", {})
    print("\nDIGITAL TWIN PRICE CALCULATION:")
    if "price_calculation" in dt:
        print(json.dumps(dt["price_calculation"], indent=2, ensure_ascii=False))
    else:
        print("  Not found.")


if __name__ == "__main__":
    asyncio.run(main())
