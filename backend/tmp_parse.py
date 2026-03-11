import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append('d:/kalk_v3/backend')
load_dotenv('d:/kalk_v3/backend/.env')
load_dotenv('d:/kalk_v3/frontend/.env.local')

async def main():
    with open(r"C:\Users\proma\Downloads\jumbo.pdf", "rb") as f:
        file_bytes = f.read()

    from core.pipeline_router import classify_document
    from core.document_converter import convert_to_gemini_input
    
    gemini_data, gemini_mime = convert_to_gemini_input(file_bytes, "application/pdf")
    doc_type, doc_meta = classify_document(gemini_data, gemini_mime)
    print("Doc type:", doc_type)
    print("Meta:", doc_meta)
    
    if doc_type == "OFFER":
        from core.pipeline_multi_vehicle import detect_and_split_vehicles
        multi = detect_and_split_vehicles(gemini_data, gemini_mime)
        if multi:
            print("Multi-vehicle count:", len(multi))
            from core.extractor_v2 import process_single_twin
            for i, v in enumerate(multi):
                print(f"Twin {i}: {v.get('brand')} {v.get('model')}")
                try:
                    res = process_single_twin(v)
                    print(f"Twin {i} extraction success: {len(res)} chars")
                except Exception as e:
                    print(f"Twin {i} extraction error:", e)
        else:
            print("Single offer")
            from core.extractor_v2 import extract_vehicle_data_v2
            try:
                res = extract_vehicle_data_v2(gemini_data, gemini_mime)
                print("Single extraction success:", len(res))
            except Exception as e:
                print("Single extraction error:", e)

if __name__ == "__main__":
    asyncio.run(main())
