import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from core.parser_schema import MappedOffer
from google import genai
from google.genai import types
from core.samar_rules import SAMAR_MARKDOWN

from core.samar_mapper import map_to_samar_class

# This approach assumes you have set GEMINI_API_KEY in your env variables.
# You could also load this from a .env file if using python-dotenv.
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY environment variable not set.")

router = APIRouter(prefix="/parse-offer", tags=["Parser"])


class ParseRequest(BaseModel):
    raw_text: str = Field(
        description="Może to być surowy JSON wygenerowany przez zewnętrzny LLM lub zrzucony tekst PDF."
    )


@router.post("", response_model=MappedOffer)
async def parse_offer_endpoint(req: ParseRequest):
    """
    Przyjmuje tekst (strukturę JSON lub surowy zrzut PDF z oferty handlowej)
    i za pomocą API Google GenAI zamienia/waliduje w ustrukturyzowany format LTR V1 (MappedOffer).
    Następnie automatycznie przypisuje twardą logiką backendową Klasę SAMAR, aby uniknąć halucynacji.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, detail="Brak klucza GEMINI_API_KEY w konfiguracji serwera."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
Jesteś systemem eksperckim branży motoryzacyjnej LTR. Twoim zadaniem jest przetłumaczenie 
surowego tekstu z oferty handlowej lub struktury JSONa na precyzyjny schemat wymagań systemu wycenowego.

Przeanalizuj poniższe dane i wyciągnij pożądane informacje. 
Zwróć uwagę:
- Złóż odpowiednią markę (np. 'Volkswagen', 'Skoda').
- Model to głowna nazwa auta, trim to wersja nadwoziowa/silnikowa.
- Podaj segment (np. A, B, C, D) i body_style (np. SUV, Hatchback), o ile można je wywnioskować.
- Wyciągnij surową nazwę lakieru / koloru do pola `color`.
- Podaj `base_price_net` przed wszelkimi rabatami (cena cennikowa).
- Opcje fabryczne (doliczane do auta przez fabrykę) umieść w `factory_options`. Ceny ujemne traktuj jako rabat/brak elementu w pakiecie.
- Opcje serwisowe / dealerskie umieść w `dealer_options`.
- Znajdź główny sumaryczny rabat (kwotowy `discount_amount_net` lub procentowy `discount_pct`).
- Wywnioskuj główne koła wycinając format "AAA/BB RCC" (np. 205/55 R16) do pola `tire_size`.
- Moc uzupełnij w KM. Skrzynię na 'automatyczna' lub 'manualna'.

Tekst / Dane oferty:
---
{req.raw_text}
---
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MappedOffer,
                temperature=0.1,
            ),
        )

        if not response.text:
            raise HTTPException(
                status_code=500, detail="Model językowy nie zwrócił danych."
            )

        parsed_dict = json.loads(response.text)

        # Odbieramy model walidowany jako słownik by zmodyfikowac samar_class
        offer_data = MappedOffer.model_validate(parsed_dict)

        # Wywołanie TWARDEGO mapowania na backendzie!
        klasa_kod, klasa_nazwa = map_to_samar_class(
            brand=offer_data.brand,
            model=offer_data.model,
            segment=offer_data.segment,
            body_style=offer_data.body_style,
        )
        offer_data.samar_class_name = f"[{klasa_kod}] {klasa_nazwa}"

        return offer_data

    except Exception as e:
        print(f"Błąd podczas parsowania oferty: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SamarCategoryRequest(BaseModel):
    brand: str = Field(description="Marka pojazdu")
    model: str = Field(description="Model pojazdu")
    body_style: str = Field(description="Typ nadwozia")


class SamarCategoryResponse(BaseModel):
    samar_category: str = Field(
        description="Przypisana Kategoria SAMAR wybierana spośród ściśle zdefiniowanych opcji."
    )


@router.post("/samar-category", response_model=SamarCategoryResponse)
async def classify_samar_category(req: SamarCategoryRequest):
    """
    Przyjmuje podstawowe dane pojazdu i używając wewnętrznej wiedzy LLM o macierzy SAMAR,
    klasyfikuje go do odgórnie zdefiniowanej grupy m.in.: 'GRUPA PODSTAWOWA', 'VANY',
    'SAMOCHODY SPORTOWO-REKREACYJNE', 'SAMOCHODY TERENOWO-REKREACYJNE', 'FURGONETKI', 'MINIBUSY', 'INNE'.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, detail="Brak klucza GEMINI_API_KEY w konfiguracji serwera."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
Jesteś ekspertem z branży motoryzacyjnej specjalizującym się w klasyfikacji pojazdów zgodnie z segmentacją rynkową IBRM SAMAR 2025.
Twoim głównym zadaniem jest bezbłędne przypisanie wskazanego pojazdu do odpowiedniej Grupy SAMAR.

Reguły segmentacji zawarte w specyfikacji:
{SAMAR_MARKDOWN}

Zwrócona kategoria w polu `samar_category` powinna brzmieć dokładnie tak, jak poniższe zatwierdzone wartości (wielkie litery!):
- GRUPA PODSTAWOWA
- VANY
- SAMOCHODY SPORTOWO-REKREACYJNE
- SAMOCHODY TERENOWO-REKREACYJNE
- FURGONETKI
- MINIBUSY
- KOMBIVANY
- INNE (tylko i wyłącznie, gdy pojazdu za nic na świecie nie podepniesz pod resztę bazując na jego marce i modelu)

Samochód do oceny:
- Marka: {req.brand}
- Model: {req.model}
- Typ nadwozia sugerowany z oferty: {req.body_style}

Pamiętaj:
1. Priorytet ma marka i model auta. Jeżeli model został wylistowany w regułach np. 'Audi Q7' jako GRUPA TERENOWO-REKREACYJNE, bezwzględnie mu to wyznacz. 
2. Jeżeli modelu brakuje na listach (np. pojazdy dostawcze jak Crafter, Sprinter, Ducato), wywnioskuj poprawną kategorię na podstawie swojej ogólnej wiedzy i typu nadwozia (np. FURGONETKI, KOMBIVANY).
3. Do grupy 'INNE' wrzucaj tylko naprawdę rzadkie i specyficzne przypadki, które nie wpisują się w żaden z pozostałych segmentów.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SamarCategoryResponse,
                temperature=0.0,  # Zero-temperature for deterministic classification
            ),
        )

        if not response.text:
            raise HTTPException(
                status_code=500, detail="Model językowy nie sklasyfikował auta."
            )

        parsed_dict = json.loads(response.text)
        return SamarCategoryResponse.model_validate(parsed_dict)

    except Exception as e:
        print(f"Błąd klasyfikacji SAMAR: {e}")
        # Domyślnie gdy LLM leży, zwróć INNE by front nie wybuchł
        return SamarCategoryResponse(samar_category="INNE")
