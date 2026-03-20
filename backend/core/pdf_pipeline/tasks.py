import os
import logging
from worker import celery_app
from core.pdf_pipeline.schemas import ExtractorPipelineResult, ParsedPriceList
from core.pdf_pipeline.extractor import PDFExtractor
from core.pdf_pipeline.agents import PricingAgent
from core.pdf_pipeline.resolver import FootnoteResolver
from core.pdf_pipeline.normalizer import StrictNormalizer

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="extract_pdf_pricelist_task")
def extract_pdf_pricelist_task(self, temp_file_path: str) -> dict:
    """
    Celery task that runs the fully deterministic and LLM-assisted PDF parsing pipeline.
    It takes a path to a temporary file, processes it, and cleans it up.
    Returns JSON-serializable representation of ExtractorPipelineResult.
    """
    try:
        logger.info(
            f"Rozpoczynam przetwarzanie taska Celery dla pliku {temp_file_path}"
        )
        self.update_state(
            state="PROCESSING", meta={"status": "Inicjalizacja", "progress": 0}
        )

        extractor = PDFExtractor()
        agent = PricingAgent()
        resolver = FootnoteResolver()
        normalizer = StrictNormalizer()

        # Step 1: Deterministic Docling Extraction
        self.update_state(
            state="PROCESSING",
            meta={"status": "Ekstrakcja tekstu z dokumentu (Docling)", "progress": 10},
        )
        raw_markdown = extractor.extract_to_markdown(temp_file_path)

        if not raw_markdown.strip():
            logger.warning("Docling zwrócił pusty Markdown")
            return ExtractorPipelineResult(
                is_successful=False,
                error_message="Z pliku PDF nie udało się wyciągnąć czytelnego tekstu. Format prawdopodobnie jest chroniony lub nieczytelny.",
                raw_markdown="",
            ).model_dump()

        # Step 2: Agentic Schema Parsing via LLM
        self.update_state(
            state="PROCESSING",
            meta={
                "status": "Analiza danych przez sztuczną inteligencję",
                "progress": 40,
            },
        )
        logger.info("Faza 2: Przekazuję markwodn do modelu językowego")
        parsed_data = agent.extract_data(raw_markdown)

        # Handling potential unparseable data returned from Agent (though it usually throws Exception)
        if not isinstance(parsed_data, ParsedPriceList):
            logger.error("Rozpoznano krytyczny błąd formatu wynikowego od Agenta")
            return ExtractorPipelineResult(
                is_successful=False,
                error_message="Agent zwrócił nieprawidłowy schemat.",
                raw_markdown=raw_markdown,
            ).model_dump()

        # Step 3: Footnote Resolution
        self.update_state(
            state="PROCESSING",
            meta={"status": "Rozwiązywanie przypisów i referencji", "progress": 75},
        )
        logger.info(
            f"Faza 3: Rozwiązywanie przypisów ({len(parsed_data.footnotes)} znaleziono)"
        )
        resolved_data = resolver.resolve(parsed_data)

        # Step 4: Strict Normalization
        self.update_state(
            state="PROCESSING",
            meta={
                "status": "Ścisła normalizacja danych i sprawdzanie błędów",
                "progress": 90,
            },
        )
        logger.info("Faza 4: Ścisła normalizacja danych (Zeroing, Cleaning)")
        final_normalized_data = normalizer.normalize(resolved_data)

        # Success result formulation
        self.update_state(
            state="PROCESSING", meta={"status": "Zakończono", "progress": 100}
        )
        logger.info("Rurociąg PDF zakończony sukcesem.")

        return ExtractorPipelineResult(
            is_successful=True,
            parsed_data=final_normalized_data,
            raw_markdown=raw_markdown,
        ).model_dump()

    except Exception as e:
        logger.exception("Błąd w trakcie przetwarzania pliku PDF:")
        return ExtractorPipelineResult(
            is_successful=False,
            error_message=f"Wewnętrzny błąd serwera podczas ekstrakcji: {str(e)}",
        ).model_dump()

    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.error(f"Nie udało się oczyścić pliku tymczasowego: {e}")
