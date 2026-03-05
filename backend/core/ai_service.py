from typing import Optional, Any
import json
from google.genai import types
from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
from core.extractor_models import VehicleBrochureSchema


def process_brochure_document(raw_text: str) -> Optional[Any]:
    """
    Funkcja (Digital Twin) do przetwarzania surowego pdf_text / json w czystą, ustandaryzowaną broszurę ofertową
    (tzw. Karta Produktu). Korzysta z zewnętrznego API Google GenAI i zwraca model Pydantic.
    """
    client = get_gemini_client()

    prompt = f"""
Jesteś zaawansowanym systemem eksperckim branży motoryzacyjnej. Twoim zadaniem jest przekształcenie 
surowego zrzutu tekstu z chaotycznej oferty dealera na czystą, idealną Broszurę Samochodu.

ZASADY KRYTYCZNE (ZŁAMIESZ=ZATRZYMANIE):
1. Pod żadnym pozorem nie zwracaj w danych wyjściowych jakichkolwiek kwot, cen (netto/brutto), rabatów ani rat finansowania! Jeśli opcja ma cenę, pomiń cenę i zapisz samą jej nazwę.
2. Ukryj całkowicie wszystkie dane osobowe klienta oraz dane identyfikacyjne dealera oferującego pojazd.
3. Analizuj mocno wyposażenie (standardowe i opcjonalne). Podziel je NA własnoręcznie stworzone, logiczne KATEGORIE, takie jak np: "Bezpieczeństwo i Systemy Wspomagające", "Komfort i Wnętrze", "Nadwozie", "Multimedia". Listuj te opcje bezcenowo.
4. Określ `vehicle_class` na "Osobowy" lub "Dostawczy". Dla aut dostawczych ZWRÓĆ szczególną uwagę na ładowność i pojemność paki.
5. Wyciągnij jak najwięcej danych technicznych wprost z pliku (w tym MASY i WYMIARY).

Surowy tekst z oferty:
---
{raw_text}
---
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VehicleBrochureSchema,
                temperature=0.1,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )

        if not response.text:
            return None

        parsed_dict = json.loads(response.text)
        return VehicleBrochureSchema.model_validate(parsed_dict)
    except Exception as e:
        print(f"Błąd podczas generowania broszury: {e}")
        return None
