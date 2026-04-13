import asyncio
from dotenv import load_dotenv
load_dotenv()
from core.extractor_v2 import ExtractorV2

async def main():
    file_path = r"C:\Users\proma\Downloads\SANTA FE Hybrid.pdf"
    extractor = ExtractorV2()
    print("Rozpoczynam ekstrakcję dla:", file_path)
    result = await extractor.extract(file_path=file_path)
    print("\n\n--- WYNIK ---")
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
