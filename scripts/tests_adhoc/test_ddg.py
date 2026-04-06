import asyncio
from core.google_search import get_service_interval_from_search
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional

load_dotenv(".env")
api_key = os.environ.get("GEMINI_API_KEY")


class ServiceIntervalSchema(BaseModel):
    service_interval_km: Optional[int] = Field(
        description="Interwał w kilometrach np. 30000. Null jeśli nie znaleziono."
    )
    service_interval_months: Optional[int] = Field(
        description="Interwał w miesiącach np. 24 (co 2 lata). Null jeśli nie znaleziono."
    )


async def run_test():
    brand = "Opel"
    model = "Astra"
    trim = ""

    # 1. Test search
    print(f"Szukam w Google dla {brand} {model}...")
    search_context = get_service_interval_from_search(brand, model, trim)
    print(f"Wynik wyszukiwania:\n{search_context}\n")

    if not search_context:
        print("Brak wyników z Google. DuckDuckGo zablokowane?")
        return

    # 2. Test LLM
    print("Odpalam drugiego pass-a LLM...")
    client = genai.Client(api_key=api_key)
    fallback_prompt = f"""
Na podstawie poniższych wyników z wyszukiwarki internetowej, wyciągnij cykl (interwał) przeglądowy 
dla samochodu {brand} {model}. 

ZASADY:
1. Szukaj dystansu (w kilometrach) i maksymalnego czasu (w miesiącach).
2. Jeśli oficjalnego interwału nie podano wprost, a artykuły często sugerują np. "wymieniaj co 15-20 tys. km lub co rok", wybierz górną rynkową granicę (np. 20000 km, 12 miesięcy).
3. Dla aut typu Opel Astra / wozów koncernu Stellantis (PSA), jeśli tekst nie daje żadnych konkretów ale dotyczy modelu, możesz w ostateczności przyjąć standardowy interwał długoterminowy: 30000 km i 12 miesięcy, chyba że kontekst ewidentnie wskazuje inaczej (np. wersje elektryczne mają co 2 lata (24 miesiące)).
4. ZAWSZE staraj się zwrócić liczby inteligentnie wywnioskowane z tekstu zamiast Null, o ile tylko tekst jakkolwiek tyczy się serwisów tego modelu.

Wyniki z Google:
{search_context}
"""
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
        print(f"Odpowiedź LLM:\n{fallback_res.text}")
    except Exception as ex:
        print(f"Błąd LLM: {ex}")


if __name__ == "__main__":
    asyncio.run(run_test())
