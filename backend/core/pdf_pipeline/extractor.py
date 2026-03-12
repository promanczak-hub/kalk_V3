from pathlib import Path
from docling.document_converter import DocumentConverter
import logging

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Class responsible for deterministic extraction of PDF content using docling."""

    def __init__(self):
        self.converter = DocumentConverter()

    def extract_to_markdown(self, pdf_path: str | Path) -> str:
        """
        Converts a given PDF file to Markdown format using docling.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            The extracted text content in Markdown format.

        Raises:
            FileNotFoundError: If the provided path does not exist.
            Exception: If the conversion process fails.
        """
        path_obj = Path(pdf_path)
        if not path_obj.exists():
            logger.error(f"File not found: {path_obj}")
            raise FileNotFoundError(f"Plik PDF nie istnieje: {path_obj}")

        logger.info(f"Rozpoczynam ekstrakcję docling dla pliku: {path_obj}")

        try:
            result = self.converter.convert(str(path_obj))
            markdown_content = result.document.export_to_markdown()
            logger.info(
                f"Ekstrakcja zakończona. Wygenerowano {len(markdown_content)} znaków MD."
            )
            return markdown_content
        except Exception as e:
            logger.error(f"Błąd podczas konwersji docling: {str(e)}")
            raise
