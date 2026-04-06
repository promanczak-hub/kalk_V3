import logging
from typing import Dict, Any
from supabase import Client
from core.extraction_pipeline.utils import (
    update_progress,
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
    """Handles documents classified as price lists or brochures by rejecting them."""

    logger.info(
        f"[BG TASK] Dokument sklasyfikowany jako cennik/broszura ({doc_meta.get('doc_type', 'UNKNOWN')}). Odrzucanie."
    )

    error_msg = "Wgrany plik został sklasyfikowany jako ogólny cennik lub broszura. System aktualnie przetwarza wyłącznie konkretne konfiguracje pojazdów i oferty."
    update_progress(supabase, file_id, f"error: {error_msg}")

    try:
        supabase.table("vehicle_synthesis").update({"verification_status": "error"}).eq(
            "id", file_id
        ).execute()
    except Exception as e:
        logger.error(
            f"[BG TASK ERROR] Nie udało się uaktualnić statusu na error dla {file_id}: {e}"
        )
