import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status

from core.pdf_pipeline.schemas import ExtractorPipelineResult, ParsedPriceList
from core.pdf_pipeline.extractor import PDFExtractor
from core.pdf_pipeline.agents import PricingAgent
from core.pdf_pipeline.resolver import FootnoteResolver
from core.pdf_pipeline.normalizer import StrictNormalizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf-pipeline", tags=["PDF Extraction Pipeline"])


@router.post("/extract", response_model=ExtractorPipelineResult)
async def extract_pdf_pricelist(file: UploadFile = File(...)):
    """
    Endpoint that accepts a PDF file and runs it through the full pipeline:
    1. Docling deterministic markdown extraction
    2. Gemini AI structured mapping to ParsedPriceList
    3. Deterministic cross-footnote resolver
    4. Strict Normalization (enforce 0.0 on None, clean strings)
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tylko pliki PDF są obsługiwane",
        )

    temp_file_path = None
    try:
        # Create a temporary file to save the uploaded PDF
        fd, temp_file_path = tempfile.mkstemp(suffix=".pdf")

        # Write chunks to disk to avoid memory overflow on huge PDFs
        with os.fdopen(fd, "wb") as f:
            while chunk := await file.read(8192):
                f.write(chunk)

        logger.info(
            f"Otrzymano plik {file.filename}, uruchamiam rurociąg PDF na {temp_file_path}"
        )

        # Pipeline Steps Initiation
        extractor = PDFExtractor()
        agent = PricingAgent()
        resolver = FootnoteResolver()
        normalizer = StrictNormalizer()

        # Step 1: Deterministic Docling Extraction
        raw_markdown = extractor.extract_to_markdown(temp_file_path)

        if not raw_markdown.strip():
            logger.warning("Docling zwrócił pusty Markdown")
            return ExtractorPipelineResult(
                is_successful=False,
                error_message="Z pliku PDF nie udało się wyciągnąć czytelnego tekstu. Format prawdopodobnie jest chroniony lub nieczytelny.",
                raw_markdown="",
            )

        # Step 2: Agentic Schema Parsing via LLM
        logger.info("Faza 2: Przekazuję markwodn do modelu językowego")
        parsed_data = agent.extract_data(raw_markdown)

        if not isinstance(parsed_data, ParsedPriceList):
            logger.error("Rozpoznano krytyczny błąd formatu wynikowego od Agenta")
            return ExtractorPipelineResult(
                is_successful=False,
                error_message="Agent zwrócił nieprawidłowy schemat.",
                raw_markdown=raw_markdown,
            )

        # Step 3: Footnote Resolution
        logger.info(
            f"Faza 3: Rozwiązywanie przypisów ({len(parsed_data.footnotes)} znaleziono)"
        )
        resolved_data = resolver.resolve(parsed_data)

        # Step 4: Strict Normalization
        logger.info("Faza 4: Ścisła normalizacja danych (Zeroing, Cleaning)")
        final_normalized_data = normalizer.normalize(resolved_data)

        # Success result formulation
        logger.info("Rurociąg PDF zakończony sukcesem.")
        return ExtractorPipelineResult(
            is_successful=True,
            parsed_data=final_normalized_data,
            raw_markdown=raw_markdown,
        )

    except Exception as e:
        logger.exception("Błąd w trakcie przetwarzania pliku PDF:")
        return ExtractorPipelineResult(
            is_successful=False,
            error_message=f"Wewnętrzny błąd serwera podczas ekstrakcji: {str(e)}",
        )

    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.error(f"Nie udało się oczyścić pliku tymczasowego: {e}")
