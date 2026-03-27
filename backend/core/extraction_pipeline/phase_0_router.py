import uuid
import logging
from typing import Dict, Any
from supabase import Client
from core.extraction_pipeline.utils import (
    update_progress,
    is_cancelled,
    normalize_brand,
)

logger = logging.getLogger(__name__)


def handle_catalog_routing(
    supabase: Client,
    file_id: str,
    file_name: str,
    file_bytes: bytes,
    mime_type: str,
    doc_meta: Dict[str, Any],
    router_data: Any,
) -> None:
    """Handles documents classified as price lists or brochures."""

    logger.info(
        "[BG TASK] Dokument sklasyfikowany jako cennik/broszura. Routing do Biblioteki Cenników."
    )
    update_progress(supabase, file_id, "processing_library_document")

    if is_cancelled(file_id, supabase):
        update_progress(supabase, file_id, "cancelled")
        return

    try:
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "pdf"
        if ext not in ("pdf", "xlsx", "csv"):
            ext = "pdf"

        cat_doc_id = str(uuid.uuid4())

        brand_val = normalize_brand(doc_meta.get("brand", "") or "Unknown")
        model_family_val = normalize_brand(doc_meta.get("model", "") or "Unknown")

        # Ensure brand and model are strings and not None
        brand_val_str = brand_val if brand_val else "Unknown"
        model_family_val_str = model_family_val if model_family_val else "Unknown"

        catalog_storage_path = (
            f"{brand_val_str}/{model_family_val_str}/{cat_doc_id}.{ext}"
        )

        logger.info(
            f"[BG TASK] Uploading routed document to catalog-documents: {catalog_storage_path}"
        )
        try:
            supabase.storage.from_("catalog-documents").upload(
                path=catalog_storage_path,
                file=file_bytes,
                file_options={"content-type": mime_type},
            )
        except Exception as u_err:
            logger.error(
                f"[BG TASK ERROR] Failed to upload to catalog-documents: {u_err}"
            )

        _DOC_TYPE_MAP = {
            "PRICE_LIST": "price_list",
            "BROCHURE": "brochure",
            "OTHER": "other",
        }
        db_doc_type = _DOC_TYPE_MAP.get(doc_meta.get("doc_type", "OTHER"), "catalog")
        mds_payload = {
            "id": cat_doc_id,
            "brand": brand_val_str,
            "model_family": model_family_val_str,
            "document_type": db_doc_type,
            "display_name": file_name,
            "is_active": True,
            "file_type": ext,
            "storage_path": catalog_storage_path,
            "original_filename": file_name,
            "file_size_bytes": len(file_bytes),
            "extraction_status": "extracting",
            "variant_count": 0,
            "document_markdown": router_data if isinstance(router_data, str) else None,
        }

        try:
            supabase.schema("reverse_search").table(
                "model_document_sources"
            ).delete().eq("brand", brand_val_str).eq(
                "model_family", model_family_val_str
            ).execute()
        except Exception as del_err:
            logger.warning(
                f"[BG TASK WARNING] Could not replace existing catalog: {del_err}"
            )

        supabase.schema("reverse_search").table("model_document_sources").insert(
            mds_payload
        ).execute()
        logger.info(
            f"[BG TASK] Dokument zapisany w model_document_sources ({cat_doc_id})."
        )

        from core.catalog_extractor import extract_catalog_variants

        try:
            cat_result = extract_catalog_variants(mds_payload)
            extracted_data = cat_result.get("extracted_data", {})
            update_payload = {
                "extraction_status": "ready",
                "extracted_data": extracted_data,
                "variant_count": cat_result.get("variant_count", 0),
                "extracted_at": "now()",
            }

            ex_brand = extracted_data.get("brand")
            if (
                ex_brand
                and str(ex_brand).strip()
                and str(ex_brand).strip().lower() != "unknown"
            ):
                update_payload["brand"] = str(ex_brand).strip().upper()

            ex_model = extracted_data.get("model_family")
            if (
                ex_model
                and str(ex_model).strip()
                and str(ex_model).strip().lower() != "unknown"
            ):
                update_payload["model_family"] = str(ex_model).strip()

            supabase.schema("reverse_search").table("model_document_sources").update(
                update_payload
            ).eq("id", cat_doc_id).execute()
            logger.info(
                f"[BG TASK] Wyekstrahowano {cat_result.get('variant_count', 0)} wariantów."
            )
        except Exception as ex_err:
            logger.error(f"[BG TASK ERROR] Błąd ekstrakcji wariantów: {ex_err}")
            supabase.schema("reverse_search").table("model_document_sources").update(
                {"extraction_status": "error", "extraction_error": str(ex_err)}
            ).eq("id", cat_doc_id).execute()

        update_progress(supabase, file_id, "moved_to_library")
        logger.info(f"[BG TASK SUCCESS] Dokument {file_id} przeniesiony do biblioteki.")
    except Exception as mds_err:
        logger.error(
            f"[BG TASK ERROR] Nie udało się przetworzyć do model_document_sources: {mds_err}"
        )
        update_progress(supabase, file_id, f"error: {str(mds_err)[:100]}")
