import os
from dotenv import load_dotenv

# Load the env variables to simulate FastAPI
load_dotenv(".env")
print("GEMINI_API_KEY defined:", bool(os.environ.get("GEMINI_API_KEY")))

from core.pipeline_digital_twin import extract_digital_twin_from_pdf


def test():
    try:
        pdf_path = "2810 JET - Opel Combo Cargo Załogowy L2 XL 102KM Diesel Manual.pdf"
        if not os.path.exists(pdf_path):
            print("File not found.")
            return

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        print(f"Loaded {len(pdf_bytes)} bytes.")
        data = extract_digital_twin_from_pdf(
            document_data=pdf_bytes,
            mime_type="application/pdf",
        )
        print("Extracted Data keys:", data.keys() if data else "Empty")
        if not data:
            print("EXTRACTION FAILED")
    except Exception as e:
        print("Global Error:", e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test()
