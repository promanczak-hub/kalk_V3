import os
import json
import logging
from google import genai

from core.pdf_pipeline.schemas import ParsedPriceList

logger = logging.getLogger(__name__)


class PricingAgent:
    """Agentic parser for extracting structured car pricing from Markdown text."""

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.5-pro"):
        """
        Initializes the agent with the Gemini client.

        Args:
            api_key: Optional API key. If not provided, it will look for GEMINI_API_KEY or GOOGLE_API_KEY.
            model_name: The Gemini model to use. Defaults to gemini-2.5-pro.
        """
        self.model_name = model_name

        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            logger.warning(
                "Brak klucza API dla Gemini. Zapytania do modelu prawdopodobnie się nie powiodą."
            )

        self.client = genai.Client(api_key=api_key)

    def extract_data(self, markdown_content: str) -> ParsedPriceList:
        """
        Extracts structured ParsedPriceList from the provided markdown content.

        Args:
            markdown_content: The document content formatted as Markdown.

        Returns:
            A populated ParsedPriceList pydantic model.

        Raises:
            Exception: If the LLM call fails or returns unparseable schema.
        """
        prompt = """
        Jesteś ekspertem motoryzacyjnym analizującym cenniki samochodowe.
        Poniżej znajduje się treść cennika przekonwertowana do formatu Markdown, ze szczególnym naciskiem na struktury tabel.
        Twoim zadaniem jest wyciągnąć wszystkie dostępne silniki oraz ich ceny w zależności od wersji wyposażenia, a także opcjonalnie listę opcji wyposażenia dodatkowego z tabel i wszelką listę przypisów do których odwołują się pozycje.
        
        Zasady:
        1. Cena powinna być liczbą typu float (zignoruj walutę, np. "zł", zignoruj spacje w dużych liczbach).
        2. Upewnij się, że poprawnie przypisujesz cenę do nazwy wersji wyposażenia (kolumny z nagłówkami np. Business, Elegance).
        3. Rozpoznaj prawidłowe ceny Netto i Brutto (jeżeli obie są podane). Jeżeli jest tylko jedna, zazwyczaj to brutto, ale to cennik B2B może podawać netto. Użyj własnego rozsądku opierając się na opisie w pliku.
        4. Wypisz wszystkie wykryte przypisy (oznaczenia umieszczane zazwyczaj drobnym drukiem przy cenach/nazwach) z cenników w sekcji footnotes wraz z ich dokładnym oznakowaniem (np. *1, (1), etc) i oryginalną treścią przypisu.
        5. Zachowaj szczególną ostrożność. Ceny wyciągnięte nie mogą zawierać pustych ciągów tam, gdzie struktura wymaga liczby. Pomiń wersje wyposażenia dla których konkretny silnik jest niedostępny.
        """

        logger.info(
            f"Wysyłanie {len(markdown_content)} znaków Markdown do analizy przez model {self.model_name}..."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=f"{prompt}\n\nDane w Markdown:\n\n{markdown_content}",
                config={
                    "response_mime_type": "application/json",
                    "response_schema": ParsedPriceList,
                    "temperature": 0.0,
                },
            )

            logger.info("Ekstrakcja LLM zakończona sukcesem.")
            # Response.text is guaranteed by explicit response_schema config to conform to JSON schema of ParsedPriceList.
            data_dict = json.loads(response.text)
            return ParsedPriceList(**data_dict)

        except Exception as e:
            logger.error(f"Błąd podczas analizy przez model Gemini: {str(e)}")
            raise
