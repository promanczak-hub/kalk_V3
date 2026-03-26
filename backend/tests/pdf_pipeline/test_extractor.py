import os
import tempfile

import pytest

from core.pdf_pipeline.extractor import PDFExtractor


def test_extractor_file_not_found() -> None:
    extractor = PDFExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract_to_markdown("nieistniejacy_plik_testowy_12345.pdf")


def test_extract_to_markdown_delegates_to_hybrid() -> None:
    """extract_to_markdown should return only the markdown string."""
    from unittest.mock import patch

    extractor = PDFExtractor()

    fd, tmp_file = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    try:
        with patch.dict("sys.modules", {"pymupdf4llm": __import__("unittest.mock", fromlist=["MagicMock"])}):
            import sys
            mock_mod = sys.modules["pymupdf4llm"]
            from unittest.mock import MagicMock
            mock_mod.to_markdown = MagicMock(return_value="# Test Markdown Output")  # type: ignore[attr-defined]

            # Need fresh extractor to pick up the mocked module
            result = extractor.extract_to_markdown(tmp_file)

            assert result == "# Test Markdown Output"
    finally:
        os.unlink(tmp_file)


def test_extract_hybrid_returns_tuple() -> None:
    """extract_hybrid should return (markdown, bytes) tuple."""
    from unittest.mock import patch, MagicMock

    fd, tmp_file = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(b"%PDF-1.4 test content")

    try:
        with patch.dict("sys.modules", {"pymupdf4llm": MagicMock()}):
            import sys
            sys.modules["pymupdf4llm"].to_markdown.return_value = "# Hybrid Test"

            extractor = PDFExtractor()
            md, pdf_bytes = extractor.extract_hybrid(tmp_file)

            assert md == "# Hybrid Test"
            assert pdf_bytes == b"%PDF-1.4 test content"
    finally:
        os.unlink(tmp_file)


def test_extractor_failure() -> None:
    """Extraction errors should propagate cleanly."""
    from unittest.mock import patch, MagicMock

    fd, tmp_file = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    try:
        with patch.dict("sys.modules", {"pymupdf4llm": MagicMock()}):
            import sys
            sys.modules["pymupdf4llm"].to_markdown.side_effect = RuntimeError("pymupdf4llm crash")

            extractor = PDFExtractor()
            with pytest.raises(RuntimeError, match="pymupdf4llm crash"):
                extractor.extract_to_markdown(tmp_file)
    finally:
        os.unlink(tmp_file)
