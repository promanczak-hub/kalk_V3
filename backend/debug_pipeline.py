import os
import json
from dotenv import load_dotenv

load_dotenv()

from core.pipeline_digital_twin import extract_digital_twin_from_pdf  # noqa: E402
from core.pipeline_card_summary import generate_card_summary_from_twin  # noqa: E402
from core.pipeline_discounts import match_fleet_discount  # noqa: E402


def test_pipeline():
    print("Testing digital twin extraction...")
    try:
        # Pass dummy pdf path or content
        pdf_path = "../skoda.pdf"
        if not os.path.exists(pdf_path):
            print("No skoda.pdf found, using dummy text")
            data = "To jest testowa oferta na samochód marki Kia Ceed 1.5 T-GDI 160KM. Cena: 120 000 PLN brutto."
            mime = "text/plain"
        else:
            with open(pdf_path, "rb") as f:
                data = f.read()
            mime = "application/pdf"

        print("1. extract_digital_twin_from_pdf")
        pro_data = extract_digital_twin_from_pdf(data, mime)
        print(
            f"Result keys: {list(pro_data.keys()) if isinstance(pro_data, dict) else 'Not a dict'}"
        )

        print("2. generate_card_summary_from_twin")
        pro_data = generate_card_summary_from_twin(pro_data)
        print(
            f"Result keys: {list(pro_data.keys()) if isinstance(pro_data, dict) else 'Not a dict'}"
        )

        print("3. match_fleet_discount")
        pro_data = match_fleet_discount(pro_data)
        print(
            f"Result keys: {list(pro_data.keys()) if isinstance(pro_data, dict) else 'Not a dict'}"
        )

        print("Full string output:")
        print(json.dumps(pro_data, ensure_ascii=False)[:500] + "...")
        print("Pipeline successful!")
    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_pipeline()
