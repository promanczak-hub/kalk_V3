import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pdf_pipeline.extractor import PDFExtractor
from core.extractor_v2 import extract_vehicle_data_v2


def main():
    pdf_path = r"C:\Users\proma\Downloads\MariuszGawareckiCBREF O R D R A N G E R 2 . 3 E C O B O O S T P H E V 2 8 1 K M A 1 0 E - 4 W DOFERTA_nr_3387_2026_04_z_dnia_2026-04-09.pdf"

    if not os.path.exists(pdf_path):
        print("Nie znaleziono pliku PDF!")
        return

    print("Rozpoczynam test pełnego potoku extractor_v2...")

    extractor = PDFExtractor()
    markdown_text = extractor.extract_to_markdown(pdf_path)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result_json_str = extract_vehicle_data_v2(
        pdf_bytes, mime_type="application/pdf", text_data=markdown_text
    )

    result = json.loads(result_json_str)

    with open("test_full_v2_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("Zapisano wynik do test_full_v2_output.json")

    card_summary = result.get("card_summary", {})
    print("CENA w card_summary:")
    print("- Base price:", card_summary.get("pricing", {}).get("base_price"))
    print("- Options price:", card_summary.get("pricing", {}).get("options_price"))
    print(
        "- Total price (gross):",
        card_summary.get("pricing", {}).get("total_price_gross"),
    )
    print(
        "- Total price (net):", card_summary.get("pricing", {}).get("total_price_net")
    )
    print("- Validation flags:", result.get("validation_flags", {}))


if __name__ == "__main__":
    main()
