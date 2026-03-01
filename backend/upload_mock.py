import os
import uuid
import hashlib
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def upload_mock():
    # 1. Setup Supabase
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    file_path = r"C:\Users\proma\Downloads\BMW 320i Touring rok produkcji 2025.pdf"

    # 2. Compute MD5
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        md5_hash = hashlib.md5(file_bytes).hexdigest()

    # 3. Check for duplicates in Supabase
    res = (
        supabase.table("vehicle_synthesis")
        .select("id")
        .eq("file_hash", md5_hash)
        .execute()
    )
    if res.data:
        print(
            f"File already in database with ID {res.data[0]['id']}, deleting it to test fresh..."
        )
        supabase.table("vehicle_synthesis").delete().eq("file_hash", md5_hash).execute()

    # 4. Create new row
    file_id = str(uuid.uuid4())
    print(f"Creating row for File ID: {file_id}")
    supabase.table("vehicle_synthesis").insert(
        {"id": file_id, "verification_status": "processing", "file_hash": md5_hash}
    ).execute()

    # 5. Send to API
    print("Sending POST request to localhost:8000/api/extract/async")
    with open(file_path, "rb") as f:
        files = {"file": ("BMW 320i Touring.pdf", f, "application/pdf")}
        data = {"file_id": file_id}
        response = requests.post(
            "http://localhost:8000/api/extract/async", files=files, data=data
        )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")


if __name__ == "__main__":
    upload_mock()
