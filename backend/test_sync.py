import os
import sys
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.background_jobs import process_and_save_document_bg

file_path = r"C:\Users\proma\Downloads\GON-26-0003978 VW Crafter Furgon L3H2 177KM 4Motion automat EXPRESS.pdf"

print("Starting background job synchronously for testing...")

with open(file_path, "rb") as f:
    file_bytes = f.read()

# We need a dummy file id to not crash supabase updates, but we'll use a random uuid
import uuid
import hashlib
from core.background_jobs import get_supabase_client

file_id = str(uuid.uuid4())
md5_hash = hashlib.md5(file_bytes).hexdigest()

supabase = get_supabase_client()
supabase.table("vehicle_synthesis").delete().eq("file_hash", md5_hash).execute()

supabase.table("vehicle_synthesis").insert(
    {"id": file_id, "verification_status": "processing", "file_hash": md5_hash}
).execute()

# Run the task directly
process_and_save_document_bg(
    file_id=file_id,
    file_bytes=file_bytes,
    file_name="VW_Crafter.pdf",
    mime_type="application/pdf",
    md5_hash=md5_hash,
)

res = (
    supabase.table("vehicle_synthesis")
    .select("synthesis_data")
    .eq("id", file_id)
    .execute()
)
if res.data and res.data[0].get("synthesis_data"):
    print("--- ZWRÓCONE DANE ---")
    data = res.data[0].get("synthesis_data", {})
    print(f"Marka: {data.get('brand')}")
    print(f"Model: {data.get('model')}")
    print(f"Trim: {data.get('mapped_ai_data', {}).get('trim_level')}")
    print(f"Transmission: {data.get('mapped_ai_data', {}).get('transmission')}")
    print(f"SAMAR: {data.get('mapped_ai_data', {}).get('samar_category')}")
    print(f"Rabat: {data.get('card_summary', {}).get('suggested_discount_pct')}")

print("Done running task.")
