import json
import requests
from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.extractor_v2 import extract_vehicle_data_v2

pdf_url = "http://127.0.0.1:54321/storage/v1/object/public/raw-vehicle-pdfs/45b14401-b00a-4a39-ac0d-3f20f539bccd-Tiguan%20(1).pdf"


def main():
    print(f"Downloading PDF from {pdf_url}...")
    try:
        resp = requests.get(pdf_url)
        resp.raise_for_status()
        pdf_bytes = resp.content
        print(f"Downloaded {len(pdf_bytes)} bytes.")
    except Exception as e:
        print(f"Failed to download PDF: {e}")
        return

    print("Running extraction v2...")
    try:
        result_json_str = extract_vehicle_data_v2(
            pdf_bytes, mime_type="application/pdf"
        )
        parsed = json.loads(result_json_str)
        print("Extraction completed. Result:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Extraction failed: {e}")


if __name__ == "__main__":
    main()
