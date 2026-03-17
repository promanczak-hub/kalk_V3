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
            import fitz
            # 1. Wyciągnięcie szybkiego tekstu przy użyciu PyMuPDF (bez OCR)
            markdown_content = ""
            with fitz.open(str(path_obj)) as doc:
                for page in doc:
                    markdown_content += page.get_text("text") + "\n\n"
            
            logger.info(f"Ekstrakcja PyMuPDF zakończona wygenerowaniem {len(markdown_content)} znaków tekstu.")
            
            # 2. Odczyt surowych bajtów do wysyłki graficznej
            with open(path_obj, "rb") as f:
                pdf_bytes = f.read()
                
            return markdown_content, pdf_bytes
            
        except Exception as e:
            logger.error(f"Błąd podczas analizy hybrydowej pliku PDF: {str(e)}")
            raise
