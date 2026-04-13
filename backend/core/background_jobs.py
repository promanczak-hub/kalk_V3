import json
import logging
import os
import re
import unicodedata
from supabase import create_client, Client, ClientOptions
from dotenv import load_dotenv

from core.extractor_v2 import extract_vehicle_data_v2
from core.json_utils import clean_json_response
from core.database import SUPABASE_URL, SUPABASE_KEY
from core.pipeline_multi_vehicle import detect_and_split_vehicles
from core.document_converter import convert_to_gemini_input
from core.pipeline_router import classify_document, DOC_TYPE_OFFER

# New pipeline imports
from core.extraction_pipeline.utils import update_progress, is_cancelled
from core.extraction_pipeline.phase_0_router import handle_catalog_routing
from core.extraction_pipeline.phase_1_twins import handle_multi_vehicles
from core.extraction_pipeline.phase_2_mapping import finalize_vehicle_pipeline

load_dotenv()
load_dotenv("../frontend/.env.local")

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    options = ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60)
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=options)


def process_and_save_document_bg(
    file_id: str,
    file_bytes: bytes,
    file_name: str,
    mime_type: str,
    md5_hash: str,
) -> None:
    """
    Background task fired by FastAPI / Celery.
    Uploads file to Storage, detects vehicle count, then either:
    - Single vehicle: runs standard pipeline (extract_vehicle_data_v2)
    - Multi vehicle: splits into N twins, processes each independently
    """
    logger.info(f"[BG TASK] Zaczynam przetwarzanie pliku {file_name} (ID: {file_id})")
    tmp_pdf_path = None

    try:
        supabase = get_supabase_client()

        # ── Stage 1: Upload do Supabase Storage ──
        update_progress(supabase, file_id, "uploading")

        sanitized_name = (
            unicodedata.normalize("NFKD", file_name)
            .encode("ASCII", "ignore")
            .decode("utf-8")
        )
        sanitized_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", sanitized_name)
        storage_path = f"{file_id}-{sanitized_name}"
        res = None

        logger.info(
            f"[BG TASK] Rozpoczynam upload HTTP do Supabase storage dla {file_id}..."
        )
        try:
            res = supabase.storage.from_("raw-vehicle-pdfs").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": mime_type},
            )
            logger.info(f"[BG TASK] Sukces uploadu HTTP do Supabase dla {file_id}.")
        except Exception as upload_err:
            logger.info(
                f"[BG TASK] Upload pominęty (plik może już istnieć lub błąd RLS): {upload_err}"
            )

        raw_pdf_url = None
        if hasattr(res, "error") and res.error:
            logger.warning(
                f"[BG TASK] Ostrzeżenie: Błąd podczas wgrywania pliku do Storage: {res.error}"
            )
        else:
            url_info = supabase.storage.from_("raw-vehicle-pdfs").get_public_url(
                storage_path
            )
            if isinstance(url_info, str):
                raw_pdf_url = url_info
            elif hasattr(url_info, "public_url"):
                raw_pdf_url = url_info.public_url

        # ── Cancel check before AI ──
        if is_cancelled(file_id, supabase):
            update_progress(supabase, file_id, "cancelled")
            logger.info(f"[BG TASK] Anulowano przed ekstrakcją AI: {file_name}")
            return

        # ── Convert non-PDF formats (XLSX) to text for Gemini ──
        gemini_data, gemini_mime = convert_to_gemini_input(file_bytes, mime_type)
        if gemini_mime == "text/plain":
            logger.info(
                f"[BG TASK] Skonwertowano {mime_type} → tekst ({len(gemini_data)} znaków)"
            )

        # ── Extract Markdown via pymupdf4llm for Router Analysis (Phase -1) ──
        router_data = gemini_data
        router_mime = gemini_mime
        tmp_pdf_path = None
        if mime_type == "application/pdf":
            from core.pdf_pipeline.extractor import PDFExtractor
            import tempfile
            import concurrent.futures

            try:
                # Save PDF to temporary file
                fd, tmp_pdf_path = tempfile.mkstemp(suffix=".pdf")
                with os.fdopen(fd, "wb") as f:
                    f.write(file_bytes)

                logger.info(
                    f"[BG TASK] Ekstrakcja pymupdf4llm z tymczasowego PDF {tmp_pdf_path}"
                )
                pdf_extractor = PDFExtractor()

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(pdf_extractor.extract_hybrid, tmp_pdf_path)
                    markdown_content, pdf_bytes = future.result(timeout=600)

                from core.markdown_formatter import format_markdown_with_llm

                logger.info("[BG TASK] Reformatowanie Markdown przez Gemini Flash...")
                markdown_content = format_markdown_with_llm(markdown_content)

                router_data = markdown_content
                router_mime = "text/plain"
            except concurrent.futures.TimeoutError:
                logger.error(
                    f"[BG TASK CRITICAL] PDF extraction timeout (600s) dla {file_name}!"
                )
                router_data = gemini_data
                router_mime = gemini_mime
            except Exception as docling_err:
                logger.error(f"[BG TASK] PDF extraction failed! Błąd: {docling_err}")
                router_data = gemini_data
                router_mime = gemini_mime

        # ── Phase -1: Document Router (Gemini Pro z pymupdf4llm/Markdown) ──
        update_progress(supabase, file_id, "classifying_document")
        logger.info(f"[BG TASK] Faza -1: Klasyfikacja dokumentu {file_name}...")
        doc_type, doc_meta = classify_document(router_data, router_mime)

        if is_cancelled(file_id, supabase):
            update_progress(supabase, file_id, "cancelled")
            return

        if doc_type != DOC_TYPE_OFFER:
            handle_catalog_routing(
                supabase,
                file_id,
                file_name,
                file_bytes,
                mime_type,
                doc_meta,
                router_data,
            )
            return

        logger.info("[BG TASK] Dokument sklasyfikowany jako OFFER. Kontynuuję proces.")

        # ── Phase 0: Multi-vehicle detection (Gemini Flash) ──
        update_progress(supabase, file_id, "detecting_vehicles")
        logger.info(f"[BG TASK] Faza 0: Wykrywanie liczby pojazdów w {file_name}...")
        multi_vehicles = detect_and_split_vehicles(gemini_data, gemini_mime)
        logger.info(
            f"[BG TASK] Faza 0 wynik: {len(multi_vehicles) if multi_vehicles else 'single'}"
        )

        if is_cancelled(file_id, supabase):
            update_progress(supabase, file_id, "cancelled")
            return

        # ── MULTI-VEHICLE PATH ──
        if multi_vehicles is not None:
            handle_multi_vehicles(
                supabase, file_id, file_name, raw_pdf_url, router_data, multi_vehicles
            )
            return

        # ── STANDARD SINGLE-VEHICLE PATH ──
        logger.info(f"[BG TASK] Wysyłam {file_name} do Gemini (single vehicle)...")

        def _pipeline_progress(status: str) -> None:
            update_progress(supabase, file_id, status)

        def _pipeline_cancel_check(fid: str = file_id, sup: Client = supabase) -> bool:
            return is_cancelled(fid, sup)

        json_response = extract_vehicle_data_v2(
            gemini_data,
            mime_type=gemini_mime,
            on_progress=_pipeline_progress,
            is_cancelled=_pipeline_cancel_check,
            text_data=router_data if isinstance(router_data, str) else None,
        )

        if is_cancelled(file_id, supabase):
            update_progress(supabase, file_id, "cancelled")
            logger.info(f"[BG TASK] Anulowano po ekstrakcji AI: {file_name}")
            return

        cleaned_json = clean_json_response(json_response)
        parsed_data = json.loads(cleaned_json)

        finalize_vehicle_pipeline(
            supabase,
            file_id,
            parsed_data,
            raw_pdf_url,
            file_id,
            router_data if isinstance(router_data, str) else None,
        )

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.error(
            f"[BG TASK ERROR] Błąd przetwarzania {file_name} (ID: {file_id}): {str(e)}\n{error_trace}"
        )
        try:
            supabase = get_supabase_client()
            error_payload = {
                "verification_status": "error",
                "notes": f"Błąd ekstrakcji: {str(e)}\n\n{error_trace}",
            }
            supabase.table("vehicle_synthesis").update(error_payload).eq(
                "id", file_id
            ).execute()
        except Exception as nest_e:
            logger.critical(
                f"[BG TASK CRITICAL] Nie udało się zaktualizować statusu błędu: {str(nest_e)}"
            )
    finally:
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            try:
                os.remove(tmp_pdf_path)
                logger.info(f"[BG TASK] Usunięto tymczasowy plik PDF: {tmp_pdf_path}")
            except Exception as e:
                logger.error(
                    f"[BG TASK] Błąd usuwania pliku tymczasowego {tmp_pdf_path}: {e}"
                )
