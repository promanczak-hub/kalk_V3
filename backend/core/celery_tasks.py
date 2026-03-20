import base64
from worker import celery_app
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

@celery_app.task(name="process_document_task_from_storage")
def process_document_task_from_storage(
    file_id: str,
    storage_path: str,
    bucket_name: str,
    file_name: str,
    mime_type: str,
    md5_hash: str,
    force_doc_type: str | None = None,
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
        force_doc_type=force_doc_type,
    )

@celery_app.task(name="extract_catalog_task")
def extract_catalog_task(catalog_id: str):
    """
    Pobiera szczegóły z bazy i wywołuje parser PDF/XLSX.
    Aktualizuje status w tabeli po zakończeniu.
    """
    from core.database import supabase as sb_client
    from core.catalog_extractor import extract_catalog_variants
    
    logger.info(f"[Celery] Start extract_catalog_task dla {catalog_id}")
    resp = sb_client.table("model_document_sources").select("*").eq("id", catalog_id).execute()
    if not resp.data:
        logger.error(f"[Celery] Nie znaleziono katalogu {catalog_id}")
        return

    catalog = resp.data[0]

    try:
        # extract_catalog_variants sam pobierze plik wg `catalog['storage_path']`
        result = extract_catalog_variants(catalog)
        sb_client.table("model_document_sources").update(
            {
                "extraction_status": "ready",
                "extracted_data": result["extracted_data"],
                "variant_count": result["variant_count"],
                "extracted_at": "now()",
                "extraction_error": None,
            }
        ).eq("id", catalog_id).execute()
        logger.info(f"[Celery] Zakończono extract_catalog_task dla {catalog_id} - wariantów: {result['variant_count']}")
    except Exception as exc:
        logger.error(f"[Celery] Błąd przetwarzania cennika {catalog_id}: {exc}")
        sb_client.table("model_document_sources").update(
            {
                "extraction_status": "error",
                "extraction_error": str(exc),
            }
        ).eq("id", catalog_id).execute()
