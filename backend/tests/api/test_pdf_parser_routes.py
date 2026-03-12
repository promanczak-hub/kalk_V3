import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.pdf_pipeline.schemas import ParsedPriceList

client = TestClient(app)


@pytest.fixture
def mock_dummy_pdf():
    # Make a tiny valid pseudo-pdf content
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"


@patch("api.pdf_parser_routes.PDFExtractor")
@patch("api.pdf_parser_routes.PricingAgent")
def test_pdf_extract_endpoint_success(
    mock_agent_class, mock_extractor_class, mock_dummy_pdf
):
    # Setup extractor Mock
    mock_extractor = MagicMock()
    mock_extractor.extract_to_markdown.return_value = "# Setup PDF Content Markdown"
    mock_extractor_class.return_value = mock_extractor

    # Setup Agent Mock
    mock_agent = MagicMock()
    valid_data = ParsedPriceList(brand="Volvo", model="XC90", engines=[])
    mock_agent.extract_data.return_value = valid_data
    mock_agent_class.return_value = mock_agent

    # Perform Request
    response = client.post(
        "/api/pdf-pipeline/extract",
        files={"file": ("test_file.pdf", mock_dummy_pdf, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_successful"] is True
    assert data["error_message"] is None
    assert data["parsed_data"]["brand"] == "Volvo"
    assert data["parsed_data"]["model"] == "XC90"
    assert data["raw_markdown"] == "# Setup PDF Content Markdown"


def test_pdf_extract_endpoint_invalid_file_extension(mock_dummy_pdf):
    response = client.post(
        "/api/pdf-pipeline/extract",
        files={"file": ("test_file.txt", mock_dummy_pdf, "text/plain")},
    )
    assert response.status_code == 400
    assert "Tylko pliki PDF" in response.json()["detail"]


@patch("api.pdf_parser_routes.PDFExtractor")
def test_pdf_extract_endpoint_empty_markdown(mock_extractor_class, mock_dummy_pdf):
    mock_extractor = MagicMock()
    mock_extractor.extract_to_markdown.return_value = "   "  # empty/whitespace
    mock_extractor_class.return_value = mock_extractor

    response = client.post(
        "/api/pdf-pipeline/extract",
        files={"file": ("test_file.pdf", mock_dummy_pdf, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_successful"] is False
    assert "chroniony lub nieczytelny" in data["error_message"]
