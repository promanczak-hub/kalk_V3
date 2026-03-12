import asyncio
from dotenv import load_dotenv

# Load explicitly here first
load_dotenv()

from core.pdf_pipeline.extractor import PDFExtractor
from core.pdf_pipeline.agents import PricingAgent
from core.pdf_pipeline.resolver import FootnoteResolver
from core.pdf_pipeline.normalizer import StrictNormalizer


async def test_real_pdf():
    pdf_path = r"G:\Mój dysk\Opis-aplikacji\PDF\CennikiNowe\Cennik Elroq RM26 RP25.pdf"
    print(f"Przetwarzanie pliku: {pdf_path}")

    # 1. Extractor
    print("Faza 1: Extractor (docling)...")
    extractor = PDFExtractor()
    markdown = extractor.extract_to_markdown(pdf_path)
    print(f"Wyciągnięto {len(markdown)} znaków.")

    # 2. Agent
    print("Faza 2: LLM Agent (gemini)...")
    agent = PricingAgent()
    parsed_data = agent.extract_data(markdown)
    print(
        f"Znaleziono {len(parsed_data.engines)} silników, {len(parsed_data.features)} features, {len(parsed_data.footnotes)} przypisów."
    )

    # 3. Resolver
    print("Faza 3: Footnote Resolver...")
    resolver = FootnoteResolver()
    resolved = resolver.resolve(parsed_data)

    # 4. Normalizer
    print("Faza 4: Strict Normalizer...")
    normalizer = StrictNormalizer()
    final_data = normalizer.normalize(resolved)

    print("Zapisywanie...")
    with open("test_pipeline_output.json", "w", encoding="utf-8") as f:
        f.write(final_data.model_dump_json(indent=2))

    print("Zakończono. Wynik w test_pipeline_output.json")


if __name__ == "__main__":
    asyncio.run(test_real_pdf())
