import os
import json
from pathlib import Path

from docling.document_converter import DocumentConverter
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Gemini client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Use fallback if expected variable differs
    api_key = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=api_key)


class TrimPricing(BaseModel):
    trim_name: str = Field(
        description="Name of the trim, e.g. Business, Elegance, R-Line"
    )
    price_netto: float = Field(
        description="Net price of the car in this trim with this engine"
    )
    price_brutto: float | None = Field(
        default=None, description="Gross price of the car"
    )


class EngineOption(BaseModel):
    engine_name: str = Field(
        description="Full name of the engine, e.g. 1.5 TSI mHEV 110 kW / 150 KM"
    )
    transmission: str = Field(
        description="Transmission type, e.g. 7-stopniowa DSG, 6-biegowa manualna"
    )
    fuel_type: str = Field(description="Fuel type, e.g. Benzyna, Diesel, Hybryda")
    prices_by_trim: list[TrimPricing] = Field(
        description="List of prices across available trims for this engine"
    )


class CarPricingExtraction(BaseModel):
    brand: str = Field(description="Car brand, e.g. Volkswagen")
    model: str = Field(description="Car model, e.g. Passat")
    engines: list[EngineOption] = Field(
        description="List of all available engines and their prices across trims"
    )


def extract_pdf_data(pdf_path: str):
    print(f"1. Starting Docling extraction for {pdf_path}...")
    converter = DocumentConverter()

    # Process the document
    result = converter.convert(pdf_path)

    # Export to Markdown
    markdown_content = result.document.export_to_markdown()

    print(
        f"2. Docling finished. Markdown generated ({len(markdown_content)} characters)."
    )

    # Save markdown for diagnostic purposes
    md_out_path = Path(pdf_path).with_suffix(".md")
    with open(md_out_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"   Markdown saved to {md_out_path}")

    print("3. Sending Markdown to Gemini 2.5 Pro for structured extraction...")

    prompt = """
    Jesteś ekspertem motoryzacyjnym analizującym cenniki samochodowe.
    Poniżej znajduje się treść cennika przekonwertowana do formatu Markdown, ze szczególnym naciskiem na struktury tabel.
    Twoim zadaniem jest wyciągnąć wszystkie dostępne silniki oraz ich ceny w zależności od wersji wyposażenia.
    
    Zasady:
    1. Cena powinna być liczbą typu float (zignoruj walutę "zł").
    2. Upewnij się, że poprawnie przypisujesz cenę do nazwy wersji wyposażenia (kolumny z nagłówkami np. Business, Elegance).
    3. Zwracaj uwagę tylko na główne ceny pojazdów, zignoruj opcjonalne wyposażenie dodatkowe (pakiety, lakiery itp.) na tym etapie.
    4. Rozpoznaj prawidłowe ceny Netto i Brutto (jeżeli obie są podane). Jeżeli jest tylko jedna, zazwyczaj to brutto, ale to cennik B2B może podawać netto. Użyj własnego rozsądku opierając się na opisie w pliku.
    """

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=f"{prompt}\n\nDane w Markdown:\n\n{markdown_content}",
        config={
            "response_mime_type": "application/json",
            "response_schema": CarPricingExtraction,
            "temperature": 0.0,
        },
    )

    print("4. Gemini extraction finished.")

    # Save JSON result
    json_out_path = str(Path(pdf_path).with_suffix("")) + "-extracted.json"
    with open(json_out_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"   JSON saved to {json_out_path}")

    # Also print it parsed
    data = json.loads(response.text)
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    pdf_file = "passat_test.pdf"
    if os.path.exists(pdf_file):
        extract_pdf_data(pdf_file)
    else:
        print(f"Error: {pdf_file} not found in the current directory.")
