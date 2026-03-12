import pytest
import json
from unittest.mock import patch, MagicMock
from core.pdf_pipeline.agents import PricingAgent
from core.pdf_pipeline.schemas import ParsedPriceList


@patch("core.pdf_pipeline.agents.genai.Client")
def test_pricing_agent_successful_extraction(mock_client_class):
    # Setup mock
    mock_client_instance = MagicMock()
    mock_models = MagicMock()
    mock_response = MagicMock()

    # Create a valid JSON response matching ParsedPriceList
    valid_data = {
        "brand": "Volkswagen",
        "model": "Passat",
        "engines": [
            {
                "engine_name": "1.5 TSI",
                "transmission": "DSG",
                "fuel_type": "Benzyna",
                "prices_by_trim": [
                    {
                        "trim_name": "Elegance",
                        "price_netto": 100000.0,
                        "price_brutto": 123000.0,
                    }
                ],
            }
        ],
    }

    mock_response.text = json.dumps(valid_data)
    mock_models.generate_content.return_value = mock_response
    mock_client_instance.models = mock_models

    mock_client_class.return_value = mock_client_instance

    # Test
    agent = PricingAgent(api_key="fake_key_123")
    # Replace the mocked client onto the agent specifically to avoid initialization bugs blocking the test
    agent.client = mock_client_instance

    result = agent.extract_data("# Tabela Konfiguracji Passata")

    assert isinstance(result, ParsedPriceList)
    assert result.brand == "Volkswagen"
    assert result.model == "Passat"
    assert len(result.engines) == 1
    assert result.engines[0].engine_name == "1.5 TSI"
    assert result.engines[0].prices_by_trim[0].trim_name == "Elegance"

    # Verify the mock was called directly
    mock_models.generate_content.assert_called_once()


@patch("core.pdf_pipeline.agents.genai.Client")
def test_pricing_agent_api_failure(mock_client_class):
    mock_client_instance = MagicMock()
    mock_models = MagicMock()
    mock_models.generate_content.side_effect = Exception("API Timeout")
    mock_client_instance.models = mock_models
    mock_client_class.return_value = mock_client_instance

    agent = PricingAgent(api_key="fake_key_123")
    agent.client = mock_client_instance

    with pytest.raises(Exception, match="API Timeout"):
        agent.extract_data("content here")
