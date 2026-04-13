import sys
import os
import asyncio
import hashlib
from uuid import uuid4

# Set up paths so we can import from backend
sys.path.insert(0, os.path.abspath("backend"))

# Load envs if needed
from dotenv import load_dotenv
load_dotenv("backend/.env")

from core.database import supabase
from core.background_jobs import process_and_save_document_bg

def main():
    file_path = r"C:\Users\proma\Downloads\SANTA FE Hybrid.pdf"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    file_name = "SANTA FE Hybrid.pdf"
    mime_type = "application/pdf"
    md5_hash = hashlib.md5(file_bytes).hexdigest()
    file_id = str(uuid4())

    print(f"File size: {len(file_bytes)} bytes")

    # Insert dummy job in vehicle_synthesis table
    response = supabase.table("vehicle_synthesis").insert({
        "id": file_id,
        "verification_status": "processing"
    }).execute()
    print("Inserted dummy job:", response.data)

    print(f"Starting synchronous processing for '{file_name}' (ID: {file_id})...")
    try:
        process_and_save_document_bg(
            file_id=file_id,
            file_bytes=file_bytes,
            file_name=file_name,
            mime_type=mime_type,
            md5_hash=md5_hash
        )
        print("Pipeline execution completed successfully.")
    except Exception as e:
        print(f"Pipeline crashed with an exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
