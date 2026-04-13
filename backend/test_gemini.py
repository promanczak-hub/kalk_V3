import os
import sys
import json

# Upewniamy się, że jesteśmy w kontekście aplikacji
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pipeline_digital_twin import extract_digital_twin_from_pdf
from core.pdf_pipeline.extractor import PDFExtractor


def main():
    pdf_path = r"C:\Users\proma\Downloads\MariuszGawareckiCBREF O R D R A N G E R 2 . 3 E C O B O O S T P H E V 2 8 1 K M A 1 0 E - 4 W DOFERTA_nr_3387_2026_04_z_dnia_2026-04-09.pdf"

    if not os.path.exists(pdf_path):
        print("Nie znaleziono pliku PDF!")
        return

    print("Rozpoczynam test ekstrakcji pipeline Gemini...")

    # 1. Pobieramy markdown
    extractor = PDFExtractor()
    markdown_text = extractor.extract_to_markdown(pdf_path)

    # 2. Wysyłamy do Gemini (symulacja tak jak w extractor_v2.py)
    # używamy samego pdf jako bytes i markdown
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pro_data = extract_digital_twin_from_pdf(
        pdf_bytes, mime_type="application/pdf", text_data=markdown_text
    )

    with open("test_twin_output.json", "w", encoding="utf-8") as f:
        json.dump(pro_data, f, ensure_ascii=False, indent=2)

    print("Zapisano wynik do test_twin_output.json")
    print(json.dumps(pro_data.get("digital_twin", {}).get("pricing", {}), indent=2))


if __name__ == "__main__":
    main()
