import sys
import os
import time
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load backend .env
load_dotenv("backend/.env")

from core.offer_generator import ExcelOfferGenerator


def test_generation():
    print("Testing ExcelOfferGenerator...")
    items = [
        {
            "brand": "VW",
            "model": "Golf GTI",
            "powertrain": "2.0 TSI 245KM",
            "term": 48,
            "mileage": 15000,
            "net_installment": 1500.50,
            "system_recommendation": "Polecany dla miłośników sportowej jazdy",
            "vin_or_config": "CONFIG-123",
            "matrix_data": [
                {
                    "duration_months": 36,
                    "annual_mileage": 10000,
                    "monthly_price_net": 1600.00,
                },
                {
                    "duration_months": 36,
                    "annual_mileage": 20000,
                    "monthly_price_net": 1800.00,
                },
                {
                    "duration_months": 48,
                    "annual_mileage": 10000,
                    "monthly_price_net": 1500.00,
                },
                {
                    "duration_months": 48,
                    "annual_mileage": 15000,
                    "monthly_price_net": 1500.50,
                },
            ],
            "factory_options": ["Pakiet Design", "Lakier Kings Red"],
            "standard_equipment": ["LED Matrix", "Digital Cockpit Pro"],
        }
    ]

    try:
        # Using the same path as in oferty_routes.py
        generator = ExcelOfferGenerator(template_path="template_oferta_v2.xlsx")
        print(f"Generator initialized with template: {generator.template_path}")

        excel_bytes = generator.generate_offer(
            client_name="Test Client Sp. z o.o.", client_nip="1234567890", items=items
        )

        # Save locally to verify if it's readable
        test_filename = f"test_offer_{int(time.time())}.xlsx"
        with open(test_filename, "wb") as f:
            f.write(excel_bytes)

        print(f"Test offer generated successfully: {test_filename}")
        print(f"File size: {len(excel_bytes)} bytes")

        return test_filename
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Generation failed: {e}")
        return None


if __name__ == "__main__":
    test_generation()
