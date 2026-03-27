import re
import unicodedata
from typing import Optional
from core.database import supabase as supabase_client


def generate_safe_storage_path(file_id: str, file_name: str) -> str:
    """Sanitize file name for Supabase storage to prevent 400 Bad Request."""
    sanitized_name = (
        unicodedata.normalize("NFKD", file_name)
        .encode("ASCII", "ignore")
        .decode("utf-8")
    )
    sanitized_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", sanitized_name)
    return f"{file_id}-{sanitized_name}"


def upload_raw_vehicle_document(
    file_bytes: bytes, storage_path: str, mime_type: str, client=None
) -> Optional[str]:
    """Uploads a raw vehicle document and returns the public URL if successful."""
    client = client or supabase_client
    try:
        res = client.storage.from_("raw-vehicle-pdfs").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime_type},
        )
        if hasattr(res, "error") and res.error:
            print(f"[STORAGE] Warning: Upload error: {res.error}")
        else:
            url_info = client.storage.from_("raw-vehicle-pdfs").get_public_url(
                storage_path
            )
            if isinstance(url_info, str):
                return url_info
            elif hasattr(url_info, "public_url"):
                return url_info.public_url
    except Exception as e:
        print(f"[STORAGE] Upload skipped or failed: {e}")
    return None
