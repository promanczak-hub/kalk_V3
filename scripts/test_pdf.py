import sys
import os
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(base_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core.extractor_v2 import extract_vehicle_data_v2

file_path = r"C:\Users\proma\Downloads\S5-Limousine-AU76137T.PDF"
print(f"Processing: {file_path}")

try:
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    result_json = extract_vehicle_data_v2(file_bytes)
    result = json.loads(result_json)
    
    card = result.get("card_summary", {})
    print(f"\n--- Price Summary ---")
    print(f"Base Price: {card.get('base_price')}")
    print(f"Options Price: {card.get('options_price')}")
    print(f"Total Price: {card.get('total_price')}")
    print(f"Valid: {card.get('_validation', {}).get('is_valid')}")
    print(f"Warnings: {json.dumps(card.get('_validation', {}).get('warnings', []), indent=2, ensure_ascii=False)}")
    
    options = card.get("paid_options", [])
    print(f"\n--- Paid Options ({len(options)}) ---")
    for opt in options:
        print(f"  - {opt.get('name')}: {opt.get('price')}")
        
except Exception as e:
    import traceback
    traceback.print_exc()
