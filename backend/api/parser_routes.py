import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from core.parser_schema import MappedOffer
from core.extractor_models import VehicleBrochureSchema
from google import genai
from google.genai import types
from core.samar_rules import SAMAR_MARKDOWN

from core.samar_mapper import map_to_samar_class

# This approach assumes you have set GEMINI_API_KEY in your env variables.
# You could also load this from a .env file if using python-dotenv.
import httpx
import fitz  # PyMuPDF
import uuid
from core.database import supabase

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

        # ====== Fallback: Cykle Serwisowe z Google ======
        if (
            offer_data.service_interval_km is None
            or offer_data.service_interval_months is None
        ):
            from core.google_search import get_service_interval_from_search

            # Zapytanie w google
            search_context = get_service_interval_from_search(
                brand=offer_data.brand,
                model=offer_data.model,
                trim=offer_data.trim or "",
            )

            if search_context:
                fallback_prompt = f"""
Na podstawie poniższych wyników z wyszukiwarki internetowej, wyciągnij cykl (interwał) przeglądowy 
dla samochodu {offer_data.brand} {offer_data.model}. 

ZASADY:
1. Szukaj dystansu (w kilometrach) i maksymalnego czasu (w miesiącach).
2. Jeśli oficjalnego interwału nie podano wprost, a artykuły często sugerują np. "wymieniaj co 15-20 tys. km lub co rok", wybierz górną rynkową granicę (np. 20000 km, 12 miesięcy).
3. Dla aut typu Opel Astra / wozów koncernu Stellantis (PSA), jeśli tekst nie daje żadnych konkretów ale dotyczy modelu, możesz w ostateczności przyjąć standardowy interwał długoterminowy: 30000 km i 12 miesięcy, chyba że kontekst ewidentnie wskazuje inaczej (np. wersje elektryczne mają co 2 lata (24 miesiące)).
4. ZAWSZE staraj się zwrócić liczby inteligentnie wywnioskowane z tekstu zamiast Null, o ile tylko tekst jakkolwiek tyczy się serwisów tego modelu.

Wyniki z Google:
{search_context}
"""

                class ServiceIntervalSchema(BaseModel):
                    service_interval_km: Optional[int] = Field(
                        description="Interwał w kilometrach np. 30000. Null jeśli nie znaleziono."
                    )
                    service_interval_months: Optional[int] = Field(
                        description="Interwał w miesiącach np. 24 (co 2 lata). Null jeśli nie znaleziono."
                    )

                try:
                    fallback_res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=fallback_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ServiceIntervalSchema,
                            temperature=0.0,
                        ),
                    )

                    if fallback_res.text:
                        fallback_data = json.loads(fallback_res.text)

                        if offer_data.service_interval_km is None and fallback_data.get(
                            "service_interval_km"
                        ):
                            offer_data.service_interval_km = fallback_data[
                                "service_interval_km"
                            ]

                        if (
                            offer_data.service_interval_months is None
                            and fallback_data.get("service_interval_months")
                        ):
                            offer_data.service_interval_months = fallback_data[
                                "service_interval_months"
                            ]

                except Exception as ex:
                    print(f"Błąd fallback LLM (Google Search) dla cykli: {ex}")
        # ================================================

        # Wywołanie TWARDEGO mapowania na backendzie!
        klasa_kod, klasa_nazwa = map_to_samar_class(
            brand=offer_data.brand,
            model=offer_data.model,
            segment=offer_data.segment,
            body_style=offer_data.body_style,
            trim=offer_data.trim,
            transmission=offer_data.transmission,
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


@router.post("/extract-brochure", response_model=VehicleBrochureSchema)
async def extract_brochure_endpoint(req: ParseRequest):
    """
    Ekstrahuje czyste informacje, klasyfikuje i zrzuca kategorie
    wyposażenia pozbawione jakichkolwiek cen czy danych identyfikujących ofertę
    (dedykowane pod Czystą Broszurę / White-label).
    """
    from core.ai_service import process_brochure_document

    result = process_brochure_document(req.raw_text)
    if not result:
        raise HTTPException(
            status_code=500, detail="Błąd generowania broszury przez model LLM."
        )
    return result


class PDFImageExtractionRequest(BaseModel):
    pdf_url: str = Field(
        description="URL do pliku PDF w Supabase Storage lub inny publicznie dostępny URL."
    )


class PDFImageExtractionResponse(BaseModel):
    images: list[str] = Field(description="Lista URLi wyekstrahowanych obrazków.")


@router.post("/extract-images", response_model=PDFImageExtractionResponse)
async def extract_images_from_pdf(req: PDFImageExtractionRequest):
    """
    Pobiera plik PDF z podanego adresu URL (Supabase), używa PyMuPDF by wyciągnąć
    wbudowane obrazy większe niż 100x100px. Uploaduje te obrazy do bucketu Supabase 'vehicles'.
    """
    try:
        # 1. Pobranie pliku z podanego URL
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(req.pdf_url)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Nie można pobrać pliku z URL. Status: {resp.status_code}",
                )

            pdf_bytes = resp.content

        # 2. Parsowanie za pomocą PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        extracted_image_urls = []
        bucket_name = "vehicles"

        # Iteracja po stronach i wbudowanych obrazach
        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)

                # Szybki filtr po atrybutach szerokosci / wysookosci
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)

                if width < 100 or height < 100:
                    continue  # ignorujemy małe ikonki

                image_bytes = base_image["image"]
                ext = base_image["ext"]

                # 3. Zapis do Supabase Storage
                unique_filename = f"extracted/{uuid.uuid4().hex}.{ext}"

                # Upload
                _ = supabase.storage.from_(bucket_name).upload(
                    path=unique_filename,
                    file=image_bytes,
                    file_options={"content-type": f"image/{ext}"},
                )

                # Pobranie publicznego urla
                public_url = supabase.storage.from_(bucket_name).get_public_url(
                    unique_filename
                )
                extracted_image_urls.append(public_url)

        return PDFImageExtractionResponse(images=extracted_image_urls)

    except Exception as e:
        print(f"Błąd wydobywania zdjęć z PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))
