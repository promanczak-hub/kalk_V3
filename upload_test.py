import os
import uuid
import time
import requests
from dotenv import load_dotenv

load_dotenv("d:/kalk_v3/backend/.env")
from core.database import supabase

pdf_path = r"C:\Users\proma\Downloads\CUPRA Terramar 2.0 TSI 204 KM 7DSG 4Drive_produkcja.pdf"

# Create UUID
file_id = str(uuid.uuid4())
print(f"Uploading file with ID {file_id}")

# 1. Rezerwacja wiersza w bazie (jak we frontendzie)
supabase.table("vehicle_synthesis").insert({
    "id": file_id,
    "verification_status": "processing",
    "file_hash": file_id # Fake hash just for test
}).execute()

# 2. Wywołanie API FastAPI
url = "http://localhost:8000/api/extract/async"
with open(pdf_path, "rb") as f:
    r = requests.post(url, data={"file_id": file_id}, files={"file": f})
    print(r.json())

# Wait a loop to check processing status
for i in range(20):
    time.sleep(5)
    resp = supabase.table("vehicle_synthesis").select("verification_status").eq("id", file_id).execute()
    status = resp.data[0]["verification_status"]
    print(f"Status: {status}")
    if status in ["completed", "error", "cancelled", "moved_to_library"]:
        break

if status == "moved_to_library":
    print("Document went to library. Checking model_document_sources...")
    cats = supabase.schema("reverse_search").table("model_document_sources").select("*").ilike("display_name", "%Terramar%").execute()
    for cat in cats.data:
        print(cat['display_name'], cat['extraction_status'])
