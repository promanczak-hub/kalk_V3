import uuid
import hashlib
from dotenv import load_dotenv
from core.background_jobs import process_and_save_document_bg

load_dotenv()
load_dotenv("../frontend/.env.local")


def run_sync():
    file_path = r"C:\Users\proma\Downloads\BMW 320i Touring rok produkcji 2025.pdf"

    with open(file_path, "rb") as f:
        file_bytes = f.read()
        md5_hash = hashlib.md5(file_bytes).hexdigest()

    file_id = str(uuid.uuid4())
    print(f"Running synchronous extraction for ID: {file_id}...")

    try:
        process_and_save_document_bg(
            file_id=file_id,
            file_bytes=file_bytes,
            file_name="BMW 320i Touring.pdf",
            mime_type="application/pdf",
            md5_hash=md5_hash,
        )
        print("Done!")
    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_sync()
