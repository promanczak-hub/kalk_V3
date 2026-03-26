from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Class responsible for hybrid extraction of PDF content: Native bytes + PyMuPDF4LLM Markdown."""

    def __init__(self):
        pass

    def extract_hybrid(self, pdf_path: str | Path) -> tuple[str, bytes]:
        """
        Reads a given PDF file and returns both its raw bytes (for Vision processing)
        and its Markdown representation (for table structure context).

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            A tuple of (markdown_content, pdf_bytes).

        Raises:
            FileNotFoundError: If the provided path does not exist.
        """
        path_obj = Path(pdf_path)
        if not path_obj.exists():
            logger.error(f"File not found: {path_obj}")
            raise FileNotFoundError(f"Plik PDF nie istnieje: {path_obj}")

        logger.info(f"Otwieranie pliku PDF do ekstrakcji hybrydowej: {path_obj}")

        try:
            import pymupdf4llm

            # 1. Wyciągnięcie strukturalnego tekstu (Markdown) przy użyciu pymupdf4llm (bez OCR)
            markdown_content = pymupdf4llm.to_markdown(str(path_obj))

            logger.info(
                f"Ekstrakcja pymupdf4llm zakończona wygenerowaniem {len(markdown_content)} znaków tekstu."
            )

            # 2. Odczyt surowych bajtów do wysyłki graficznej
            with open(path_obj, "rb") as f:
                pdf_bytes = f.read()

            return markdown_content, pdf_bytes

        except Exception as e:
            logger.error(f"Błąd podczas analizy hybrydowej pliku PDF: {str(e)}")
            raise

    def extract_to_markdown(self, pdf_path: str | Path) -> str:
        """Extract only Markdown text from a PDF file using pymupdf4llm.

        Convenience wrapper over ``extract_hybrid`` for callers that do not
        need the raw PDF bytes (e.g. the pricing-pipeline Celery task).

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Markdown representation of the PDF content.

        Raises:
            FileNotFoundError: If the provided path does not exist.
        """
        markdown_content, _ = self.extract_hybrid(pdf_path)
        return markdown_content
