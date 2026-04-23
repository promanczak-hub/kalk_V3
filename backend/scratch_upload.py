import sys
import os

# add backend path
sys.path.append(os.path.abspath("d:/kalk_v3/backend"))

from core.background_jobs import process_and_save_document_bg
import uuid


def test_upload(pdf_path: str):
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    file_id = str(uuid.uuid4())
    print(f"File ID: {file_id}")

    from core.database import supabase as supabase_client

    supabase_client.table("vehicle_synthesis").insert(
        {
            "id": file_id,
            "verification_status": "new",
            "brand": "Unknown",
            "model": "Unknown",
        }
    ).execute()

    process_and_save_document_bg(
        file_id=file_id,
        file_bytes=file_bytes,
        file_name=os.path.basename(pdf_path),
        mime_type="application/pdf",
        md5_hash="dummy",
    )


if __name__ == "__main__":
    pdf_path = r"C:\Users\proma\Downloads\SANTA FE Hybrid.pdf"
    test_upload(pdf_path)
