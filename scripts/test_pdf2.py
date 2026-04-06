import sys
import os
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(base_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core.extractor_v2 import extract_vehicle_data_v2

file_path = r"C:\Users\proma\Downloads\S5-Limousine-AU76137T.PDF"

with open(file_path, "rb") as f:
    file_bytes = f.read()

result_json = extract_vehicle_data_v2(file_bytes)
with open("test_out.json", "w", encoding="utf-8") as f:
    f.write(result_json)
