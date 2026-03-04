from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")

from core.extractor_v2 import extract_vehicle_data_v2

file_path = "2810 JET - Opel Combo Cargo Załogowy L2 XL 102KM Diesel Manual.pdf"

with open(file_path, "rb") as f:
    file_bytes = f.read()

print("Extracting directly with latest code...")
json_response = extract_vehicle_data_v2(file_bytes, mime_type="application/pdf")

with open("combo_local_result.json", "w", encoding="utf-8") as f:
    f.write(json_response)
print("Done. Saved to combo_local_result.json")
