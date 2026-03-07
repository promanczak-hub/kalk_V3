import json
import datetime
import threading
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
from core.extractor_v2 import extract_vehicle_data_v2, process_single_twin
from core.json_utils import clean_json_response
from core.database import SUPABASE_URL, SUPABASE_KEY
from core.pipeline_multi_vehicle import detect_and_split_vehicles
from core.document_converter import convert_to_gemini_input
from services.ai_mapper_service import map_vehicle_data_flash

# Upewniamy się, że środowisko jest załadowane (szczególnie jeśli odpalamy lokalnie)
load_dotenv()
load_dotenv("../frontend/.env.local")

# ───── Cancel registry ─────
# Thread-safe dict of file_id → threading.Event
# When event is set, the background job should stop ASAP.
_cancel_events: dict[str, threading.Event] = {}
_cancel_lock = threading.Lock()


def register_cancel_event(file_id: str) -> threading.Event:
    """Create and register a cancellation event for a file."""
    event = threading.Event()
    with _cancel_lock:
        _cancel_events[file_id] = event
    return event


def trigger_cancel(file_id: str) -> bool:
    """Signal cancellation for a running job. Returns True if event was found."""
    with _cancel_lock:
        event = _cancel_events.get(file_id)
    if event:
        event.set()
        return True
    return False


def _cleanup_cancel_event(file_id: str) -> None:
    """Remove cancel event after job finishes."""
    with _cancel_lock:
        _cancel_events.pop(file_id, None)


# ───── Progress helpers ─────


def _update_progress(supabase: Client, file_id: str, status: str) -> None:
    """Update verification_status in DB — triggers Supabase Realtime."""
    try:
        supabase.table("vehicle_synthesis").update(
            {
                "verification_status": status,
                "processing_updated_at": datetime.datetime.utcnow().isoformat(),
            }
        ).eq("id", file_id).execute()
        print(f"[PROGRESS] {file_id} → {status}")
    except Exception as e:
        print(f"[PROGRESS ERROR] Failed to update status to '{status}': {e}")


def _is_cancelled(cancel_event: threading.Event) -> bool:
    """Check if cancellation was requested (non-blocking)."""
    return cancel_event.is_set()


def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _finalize_vehicle(
    supabase: Client,
    vehicle_id: str,
    parsed_data: dict,
    raw_pdf_url: str | None,
    cancel_event: threading.Event,
) -> None:
    """
    Shared post-extraction logic: AI mapping, SAMAR, engine class, DB save.

    Used by both single-vehicle and multi-vehicle flows.
    """
    brand = parsed_data.get("brand")
    model = parsed_data.get("model")
    offer_number = parsed_data.get("offer_number")
    if not offer_number and "metadata" in parsed_data:
        offer_number = parsed_data["metadata"].get("offer_number")

    if _is_cancelled(cancel_event):
        _update_progress(supabase, vehicle_id, "cancelled")
        return

    _update_progress(supabase, vehicle_id, "mapping_data")
    print(f"[BG TASK] Mapowanie AI (Gemini Flash) dla {vehicle_id}...")
    try:
        mapped_data = map_vehicle_data_flash(parsed_data)

        if not brand or brand == "Brak":
            brand = mapped_data.get("brand", brand)
        if not model or model == "Brak":
            model = mapped_data.get("model", model)

        card_summary = parsed_data.get("card_summary", {})
        trim = mapped_data.get("trim")

        # ── 1. Engine mapper (first — doesn't depend on SAMAR) ──
        from core.engine_mapper import map_to_engine_class

        powertrain = (
            card_summary.get("powertrain", {})
            if isinstance(card_summary.get("powertrain"), dict)
            else {}
        )
        engine_designation = powertrain.get("engine_designation")
        capacity = powertrain.get("engine_capacity")
        power = card_summary.get("power_hp")

        eng_name, eng_cat, eng_candidates = map_to_engine_class(
            fuel=mapped_data.get("fuel"),
            engine_designation=engine_designation,
            power=str(power) if power else None,
            capacity=str(capacity) if capacity else None,
            model=model,
            trim=trim,
        )

        if eng_name != "UNKNOWN":
            mapped_data["fuel"] = eng_name
            mapped_data["engine_class"] = eng_cat
            mapped_data["engine_candidates"] = eng_candidates
        elif mapped_data.get("fuel"):
            # Fallback for when API fails so we don't break old logic
            try:
                engines_resp = (
                    supabase.table("engines")
                    .select("category")
                    .eq("name", mapped_data.get("fuel"))
                    .execute()
                )
                if engines_resp.data:
                    mapped_data["engine_class"] = engines_resp.data[0]["category"]
            except Exception as db_e:
                print(f"[BG TASK] Błąd pobierania kategorii silnika fallback: {db_e}")

        # ── 2. SAMAR mapper (last — uses full context incl. seats) ──
        from core.samar_mapper import map_to_samar_class

        segment = card_summary.get("segment") or card_summary.get("car_segment")
        body_style = card_summary.get("body_style")
        transmission = mapped_data.get("transmission")
        seats_raw = card_summary.get("number_of_seats")

        samar_code, samar_name, samar_candidates = map_to_samar_class(
            brand=brand,
            model=model,
            segment=segment,
            body_style=body_style,
            trim=trim,
            transmission=transmission,
            number_of_seats=int(seats_raw) if seats_raw else None,
        )
        mapped_data["samar_category"] = samar_name
        mapped_data["samar_candidates"] = samar_candidates

        parsed_data["mapped_ai_data"] = mapped_data

    except Exception as map_err:
        print(f"[BG TASK] Błąd mapowania danych AI: {map_err}")

    if _is_cancelled(cancel_event):
        _update_progress(supabase, vehicle_id, "cancelled")
        return

    update_payload = {
        "brand": brand,
        "model": model,
        "offer_number": offer_number,
        "synthesis_data": parsed_data,
        "verification_status": "completed",
        "raw_pdf_url": raw_pdf_url,
        "document_category": parsed_data.get("card_summary", {}).get("vehicle_class"),
    }

    print(f"[BG TASK] Zapisuję wyniki do DB dla {vehicle_id}")
    supabase.table("vehicle_synthesis").update(update_payload).eq(
        "id", vehicle_id
    ).execute()
    print(f"[BG TASK] Gotowe dla {vehicle_id}")


def process_and_save_document_bg(
    file_id: str, file_bytes: bytes, file_name: str, mime_type: str, md5_hash: str
) -> None:
    """
    Background task fired by FastAPI.

    Uploads file to Storage, detects vehicle count, then either:
    - Single vehicle: runs standard pipeline (extract_vehicle_data_v2)
    - Multi vehicle: splits into N twins, processes each independently

    Supports real-time progress tracking and cancellation between stages.
    """
    cancel_event = register_cancel_event(file_id)
    print(f"[BG TASK] Zaczynam przetwarzanie pliku {file_name} (ID: {file_id})")

    try:
        supabase = get_supabase_client()

        # ── Stage 1: Upload do Supabase Storage ──
        _update_progress(supabase, file_id, "uploading")

        import tempfile
        import os

        storage_path = f"{file_id}-{file_name}"
        res = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name

            res = supabase.storage.from_("raw-vehicle-pdfs").upload(
                path=storage_path,
                file=tmp_file_path,
                file_options={"content-type": mime_type},
            )
        finally:
            if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

        raw_pdf_url = None
        if hasattr(res, "error") and res.error:
            print(
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
        if _is_cancelled(cancel_event):
            _update_progress(supabase, file_id, "cancelled")
            print(f"[BG TASK] Anulowano przed ekstrakcją AI: {file_name}")
            return

        # ── Convert non-PDF formats (XLSX) to text for Gemini ──
        gemini_data, gemini_mime = convert_to_gemini_input(file_bytes, mime_type)
        if gemini_mime == "text/plain":
            print(
                f"[BG TASK] Skonwertowano {mime_type} → tekst ({len(gemini_data)} znaków)"
            )

        # ── Phase 0: Multi-vehicle detection (Gemini Flash) ──
        _update_progress(supabase, file_id, "detecting_vehicles")
        print(f"[BG TASK] Faza 0: Wykrywanie liczby pojazdów w {file_name}...")
        multi_vehicles = detect_and_split_vehicles(gemini_data, gemini_mime)
        print(
            f"[BG TASK] Faza 0 wynik: "
            f"{'multi (' + str(len(multi_vehicles)) + ' pojazdów)' if multi_vehicles else 'single vehicle'}"
        )

        if _is_cancelled(cancel_event):
            _update_progress(supabase, file_id, "cancelled")
            return

        # ───────────────────────────────────────────────────────
        #  MULTI-VEHICLE PATH: N > 1 vehicles detected
        # ───────────────────────────────────────────────────────
        if multi_vehicles is not None:
            vehicle_count = len(multi_vehicles)
            print(
                f"[BG TASK] ★ Wykryto {vehicle_count} pojazdów w {file_name}! "
                f"Rozdzielam na osobne rekordy..."
            )

            # Existing file_hash from the parent row — retrieve it
            parent_row = (
                supabase.table("vehicle_synthesis")
                .select("file_hash")
                .eq("id", file_id)
                .single()
                .execute()
            )
            parent_hash = parent_row.data.get("file_hash") if parent_row.data else None

            for idx, vehicle_twin in enumerate(multi_vehicles):
                if _is_cancelled(cancel_event):
                    _update_progress(supabase, file_id, "cancelled")
                    return

                vehicle_label = (
                    f"{vehicle_twin.get('brand', '?')} {vehicle_twin.get('model', '?')}"
                )

                if idx == 0:
                    # Parent row becomes vehicle #1 (Opcja A)
                    current_id = file_id
                    print(
                        f"[BG TASK] Pojazd {idx + 1}/{vehicle_count}: "
                        f"{vehicle_label} (rodzic {current_id})"
                    )
                else:
                    # Create new row for vehicles 2..N
                    current_id = str(uuid.uuid4())
                    supabase.table("vehicle_synthesis").insert(
                        {
                            "id": current_id,
                            "verification_status": "processing",
                            "file_hash": parent_hash,
                        }
                    ).execute()
                    print(
                        f"[BG TASK] Pojazd {idx + 1}/{vehicle_count}: "
                        f"{vehicle_label} (nowy ID: {current_id})"
                    )

                # Update progress for this specific vehicle
                _update_progress(
                    supabase,
                    current_id,
                    f"extracting_twin_{idx + 1}_of_{vehicle_count}",
                )

                # Process twin through stages 2-3 (card_summary + discounts)
                def _child_progress(status: str, vid: str = current_id) -> None:
                    _update_progress(supabase, vid, status)

                def _child_cancel(evt: threading.Event = cancel_event) -> bool:
                    return _is_cancelled(evt)

                twin_json = process_single_twin(
                    vehicle_twin,
                    on_progress=_child_progress,
                    is_cancelled=_child_cancel,
                )

                if _is_cancelled(cancel_event):
                    _update_progress(supabase, current_id, "cancelled")
                    return

                parsed_data = json.loads(clean_json_response(twin_json))

                # Finalize: mapping, SAMAR, engine class, DB save
                _finalize_vehicle(
                    supabase, current_id, parsed_data, raw_pdf_url, cancel_event
                )

            print(
                f"[BG TASK] ★ Zakończono przetwarzanie {vehicle_count} "
                f"pojazdów z {file_name}"
            )
            return

        # ───────────────────────────────────────────────────────
        #  STANDARD SINGLE-VEHICLE PATH (unchanged logic)
        # ───────────────────────────────────────────────────────
        print(f"[BG TASK] Wysyłam {file_name} do Gemini (single vehicle)...")

        def _pipeline_progress(status: str) -> None:
            _update_progress(supabase, file_id, status)

        def _pipeline_cancel_check() -> bool:
            return _is_cancelled(cancel_event)

        json_response = extract_vehicle_data_v2(
            gemini_data,
            mime_type=gemini_mime,
            on_progress=_pipeline_progress,
            is_cancelled=_pipeline_cancel_check,
        )

        if _is_cancelled(cancel_event):
            _update_progress(supabase, file_id, "cancelled")
            print(f"[BG TASK] Anulowano po ekstrakcji AI: {file_name}")
            return

        cleaned_json = clean_json_response(json_response)
        parsed_data = json.loads(cleaned_json)

        _finalize_vehicle(supabase, file_id, parsed_data, raw_pdf_url, cancel_event)

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        print(
            f"[BG TASK ERROR] Wystąpił błąd podczas przetwarzania {file_name} "
            f"(ID: {file_id}): {str(e)}\n{error_trace}"
        )
        try:
            # Always ensure a fresh client is used in the exception block if previous one died
            supabase = get_supabase_client()
            error_payload = {
                "verification_status": "error",
                "notes": f"Błąd ekstrakcji: {str(e)}\n\n{error_trace}",
            }
            supabase.table("vehicle_synthesis").update(error_payload).eq(
                "id", file_id
            ).execute()
        except Exception as nest_e:
            print(
                f"[BG TASK CRITICAL] Nie udało się nawet zaktualizować "
                f"statusu błędu w DB: {str(nest_e)}"
            )
    finally:
        _cleanup_cancel_event(file_id)
