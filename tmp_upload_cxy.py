import os
import uuid
import time
import requests
import sys
sys.path.append(r"d:\kalk_v3\backend")
from dotenv import load_dotenv

load_dotenv("d:/kalk_v3/backend/.env")
from core.database import supabase

pdf_path = r"C:\Users\proma\Downloads\car-card-CXY6G6NG.pdf"

file_id = str(uuid.uuid4())
print(f"Uploading file with ID {file_id}")

supabase.table("vehicle_synthesis").insert({
    "id": file_id,
    "verification_status": "processing",
    "file_hash": file_id 
}).execute()

url = "http://localhost:8000/api/extract/async"
with open(pdf_path, "rb") as f:
    files = {'file': ('car-card-CXY6G6NG.pdf', f, 'application/pdf')}
    r = requests.post(url, data={"file_id": file_id}, files=files)
    print("API Response:", r.json())

for i in range(20):
    time.sleep(5)
    resp = supabase.table("vehicle_synthesis").select("verification_status").eq("id", file_id).execute()
    if not resp.data:
        print("Waiting for row...")
        continue
    status = resp.data[0]["verification_status"]
    print(f"Status: {status}")
    if status in ["completed", "error", "cancelled", "moved_to_library"]:
        break

if status == "moved_to_library":
    print("Document went to library. Checking model_document_sources...")
    cats = supabase.schema("reverse_search").table("model_document_sources").select("*").ilike("display_name", "%CXY6G6NG%").execute()
    for cat in cats.data:
        print(cat['display_name'], cat['extraction_status'])
