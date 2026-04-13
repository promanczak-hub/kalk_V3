import base64
from core.celery_app import celery_app
from core.background_jobs import process_and_save_document_bg
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document_task")
def process_document_task(
    file_id: str,
    file_b64: str,
    file_name: str,
    mime_type: str,
    md5_hash: str,
):
    # Decode file bytes from base64
    file_bytes = base64.b64decode(file_b64)
    # Run the existing heavy background job
    process_and_save_document_bg(
        file_id=file_id,
        file_bytes=file_bytes,
        file_name=file_name,
        mime_type=mime_type,
        md5_hash=md5_hash,
    )


@celery_app.task(name="process_document_task_from_storage")
def process_document_task_from_storage(
    file_id: str,
    storage_path: str,
    bucket_name: str,
    file_name: str,
    mime_type: str,
    md5_hash: str,
):
    """
    Pobiera plik z Supabase Storage i odpala analizę, omijając base64 over Redis.
    """
    from core.database import supabase as sb_client
    from urllib.parse import quote

    encoded_path = quote(storage_path, safe="/")
    logger.info(f"[Celery] Pobieranie {encoded_path} z bucketu {bucket_name}")

    # Download file from storage
    file_bytes = sb_client.storage.from_(bucket_name).download(encoded_path)

    # Run heavy job
    logger.info(f"[Celery] Uruchamianie process_and_save_document_bg dla {file_id}")
    process_and_save_document_bg(
        file_id=file_id,
        file_bytes=file_bytes,
        file_name=file_name,
        mime_type=mime_type,
        md5_hash=md5_hash,
    )
