import uuid
import json
import logging
from typing import List, Dict, Any
from supabase import Client
from core.extractor_v2 import process_single_twin
from core.json_utils import clean_json_response
from core.extraction_pipeline.utils import update_progress, is_cancelled
from core.extraction_pipeline.phase_2_mapping import finalize_vehicle_pipeline

logger = logging.getLogger(__name__)


def handle_multi_vehicles(
    supabase: Client,
    file_id: str,
    file_name: str,
    raw_pdf_url: str | None,
    router_data: Any,
    multi_vehicles: List[Dict[str, Any]],
) -> None:
    """Processes documents where multiple vehicles are detected."""
    vehicle_count = len(multi_vehicles)
    logger.info(
        f"[BG TASK] ★ Wykryto {vehicle_count} pojazdów w {file_name}! Rozdzielam na osobne rekordy..."
    )

    parent_row = (
        supabase.table("vehicle_synthesis")
        .select("file_hash")
        .eq("id", file_id)
        .single()
        .execute()
    )
    parent_hash = parent_row.data.get("file_hash") if parent_row.data else None

    for idx, vehicle_twin in enumerate(multi_vehicles):
        if is_cancelled(file_id, supabase):
            update_progress(supabase, file_id, "cancelled")
            return

        vehicle_label = (
            f"{vehicle_twin.get('brand', '?')} {vehicle_twin.get('model', '?')}"
        )

        if idx == 0:
            current_id = file_id
            logger.info(
                f"[BG TASK] Pojazd {idx + 1}/{vehicle_count}: {vehicle_label} (rodzic {current_id})"
            )
        else:
            current_id = str(uuid.uuid4())
            supabase.table("vehicle_synthesis").insert(
                {
                    "id": current_id,
                    "verification_status": "processing",
                    "file_hash": parent_hash,
                }
            ).execute()
            logger.info(
                f"[BG TASK] Pojazd {idx + 1}/{vehicle_count}: {vehicle_label} (nowy ID: {current_id})"
            )

        update_progress(
            supabase,
            current_id,
            f"extracting_twin_{idx + 1}_of_{vehicle_count}",
        )

        def _child_progress(status: str, vid: str = current_id) -> None:
            update_progress(supabase, vid, status)

        def _child_cancel(fid: str = file_id, sup: Client = supabase) -> bool:
            return is_cancelled(fid, sup)

        twin_json = process_single_twin(
            vehicle_twin,
            on_progress=_child_progress,
            is_cancelled=_child_cancel,
        )

        if _child_cancel():
            update_progress(supabase, current_id, "cancelled")
            return

        parsed_data = json.loads(clean_json_response(twin_json))

        finalize_vehicle_pipeline(
            supabase,
            current_id,
            parsed_data,
            raw_pdf_url,
            file_id,
            router_data if isinstance(router_data, str) else None,
        )

    logger.info(
        f"[BG TASK] ★ Zakończono przetwarzanie {vehicle_count} pojazdów z {file_name}"
    )
