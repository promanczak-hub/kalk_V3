import os
import json
import requests
from dotenv import load_dotenv

from core.pipeline_digital_twin import extract_digital_twin_from_pdf

load_dotenv()
load_dotenv("../frontend/.env.local")

pdf_url = "http://127.0.0.1:54321/storage/v1/object/public/raw-vehicle-pdfs/45b14401-b00a-4a39-ac0d-3f20f539bccd-Tiguan%20(1).pdf"


def main():
    print(f"Downloading PDF from {pdf_url}...")
    resp = requests.get(pdf_url)
    resp.raise_for_status()
    pdf_bytes = resp.content
    print(f"Downloaded {len(pdf_bytes)} bytes.")

    # We will temporarily mock the primary response failing to force the fallback
    # Wait, the primary response naturally fails on this PDF anyway.

    print("Running pipeline...")
    result = extract_digital_twin_from_pdf(pdf_bytes, "application/pdf")

    print("\n\n--- FINAL OUTPUT ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
