import base64
from worker import celery_app
from core.background_jobs import process_and_save_document_bg


@celery_app.task(name="process_document_task")
def process_document_task(
    file_id: str,
    file_b64: str,
    file_name: str,
    mime_type: str,
    md5_hash: str,
    force_doc_type: str | None = None,
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
        force_doc_type=force_doc_type,
    )
