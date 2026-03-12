import pytest
from unittest.mock import patch, MagicMock
from core.pdf_pipeline.extractor import PDFExtractor


def test_extractor_file_not_found():
    extractor = PDFExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract_to_markdown("nieistniejacy_plik_testowy_12345.pdf")


@patch("core.pdf_pipeline.extractor.DocumentConverter")
def test_extractor_success(mock_converter_class):
    # Setup mock
    mock_converter_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "# Test Markdown Output"
    mock_converter_instance.convert.return_value = mock_result

    mock_converter_class.return_value = mock_converter_instance

    # Create temp file
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        extractor = PDFExtractor()
        # Dependency injection / use mock
        extractor.converter = mock_converter_instance

        result = extractor.extract_to_markdown(tmp_path)

        assert result == "# Test Markdown Output"
        mock_converter_instance.convert.assert_called_once_with(tmp_path)
    finally:
        import os

        os.unlink(tmp_path)


@patch("core.pdf_pipeline.extractor.DocumentConverter")
def test_extractor_failure(mock_converter_class):
    mock_converter_instance = MagicMock()
    mock_converter_instance.convert.side_effect = Exception("General docling error")

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        extractor = PDFExtractor()
        extractor.converter = mock_converter_instance

        with pytest.raises(Exception, match="General docling error"):
            extractor.extract_to_markdown(tmp_path)
    finally:
        import os

        os.unlink(tmp_path)
