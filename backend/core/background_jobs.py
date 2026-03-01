import json
from supabase import create_client, Client
from dotenv import load_dotenv
from core.extractor_v2 import extract_vehicle_data_v2
from core.json_utils import clean_json_response
from core.database import SUPABASE_URL, SUPABASE_KEY
from services.ai_mapper_service import map_vehicle_data_flash

# Upewniamy się, że środowisko jest załadowane (szczególnie jeśli odpalamy lokalnie)
load_dotenv()
load_dotenv("../frontend/.env.local")


def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def process_and_save_document_bg(
    file_id: str, file_bytes: bytes, file_name: str, mime_type: str, md5_hash: str
) -> None:
    """
    Funkcja odpalana w tle przez FastAPI (BackgroundTasks).
    Wgrywa plik PDF do Storage, procesuje Gemini, a następnie zapisuje wynik w vehicle_synthesis.
    """
    print(f"[BG TASK] Zaczynam przetwarzanie pliku {file_name} (ID: {file_id})")

    try:
        supabase = get_supabase_client()

        # 1. Wgranie pliku fizycznego do Supabase Storage
        storage_path = f"{file_id}-{file_name}"
        res = supabase.storage.from_("raw-vehicle-pdfs").upload(
            path=storage_path, file=file_bytes, file_options={"content-type": mime_type}
        )

        # Nawet na błędzie uploadu staramy się procesować dalej
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

        # 2. Ekstrakcja danych przez Gemini AI
        print(f"[BG TASK] Wysyłam {file_name} do Gemini...")
        json_response = extract_vehicle_data_v2(file_bytes, mime_type=mime_type)
        cleaned_json = clean_json_response(json_response)
        parsed_data = json.loads(cleaned_json)

        # 3. Zapis wyniku do bazy (vehicle_synthesis)
        brand = parsed_data.get("brand")
        model = parsed_data.get("model")
        offer_number = parsed_data.get("offer_number")
        if not offer_number and "metadata" in parsed_data:
            offer_number = parsed_data["metadata"].get("offer_number")

        print(f"[BG TASK] Mapowanie AI (Gemini Flash) dla {file_name}...")
        try:
            mapped_data = map_vehicle_data_flash(parsed_data)
            parsed_data["mapped_ai_data"] = mapped_data

            # Wzbogać braki o zmapowane dane jeśli to możliwe
            if not brand or brand == "Brak":
                brand = mapped_data.get("brand", brand)
            if not model or model == "Brak":
                model = mapped_data.get("model", model)

        except Exception as map_err:
            print(f"[BG TASK] Błąd mapowania danych AI: {map_err}")

        update_payload = {
            "brand": brand,
            "model": model,
            "offer_number": offer_number,
            "synthesis_data": parsed_data,
            "verification_status": "completed",
            "raw_pdf_url": raw_pdf_url,
        }

        print(f"[BG TASK] Zapisuję wyniki Gemini do DB dla {file_id}")
        supabase.table("vehicle_synthesis").update(update_payload).eq(
            "id", file_id
        ).execute()
        print(f"[BG TASK] Gotowe dla {file_name} (ID: {file_id})")

    except Exception as e:
        print(
            f"[BG TASK ERROR] Wystąpił błąd podczas przetwarzania {file_name} (ID: {file_id}): {str(e)}"
        )
        # Zapisz błąd w bazie, żeby UI mogło to odczytać
        try:
            supabase = get_supabase_client()
            error_payload = {
                "verification_status": "error",
                "notes": f"Błąd ekstrakcji: {str(e)}",
            }
            supabase.table("vehicle_synthesis").update(error_payload).eq(
                "id", file_id
            ).execute()
        except Exception as nest_e:
            print(
                f"[BG TASK CRITICAL] Nie udało się nawet zaktualizować statusu błędu w DB: {str(nest_e)}"
            )
