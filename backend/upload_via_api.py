import httpx
import os
import uuid
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

sb = create_client(url, key)

filepath = r"C:\Users\proma\Downloads\KA1XST26262601C.pdf"
api_url = "http://localhost:8000/api/extract/async"

if not os.path.exists(filepath):
    print(f"File not found: {filepath}")
    sys.exit(1)

file_id = str(uuid.uuid4())

print(f"Reserving vehicle_synthesis row with ID: {file_id}")
sb.table("vehicle_synthesis").insert({
    "id": file_id,
    "verification_status": "processing",
    "file_hash": file_id
}).execute()

print(f"Sending file to API {api_url}...")
with open(filepath, "rb") as f:
    files = {"file": ("KA1XST26262601C.pdf", f, "application/pdf")}
    data = {"file_id": file_id}
    resp = httpx.post(api_url, files=files, data=data, timeout=30.0)
    print("API Status:", resp.status_code)
    print("API Response:", resp.json())

print("Wait for Celery to process the file in the background!")
