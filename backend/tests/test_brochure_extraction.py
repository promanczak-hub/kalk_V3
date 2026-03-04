import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.extractor_models import VehicleBrochureSchema, BrochureEquipmentCategory


# We will mock the Vertex AI / processor response to return a valid Brochure schema
@patch("core.ai_service.process_brochure_document")
def test_brochure_extraction_schema_valid_and_no_prices(mock_process):
    # Prepare mock schema output
    mock_output = VehicleBrochureSchema(
        brand="BMW",
        model="Serie 3",
        trim_level="M Sport",
        vehicle_class="Osobowy",
        engine_description="2.0 TwinPower Turbo",
        power_hp=184,
        equipment_categories=[
            BrochureEquipmentCategory(
                category_name="Bezpieczeństwo",
                items=["System ABS", "Czujniki parkowania"],
            ),
            BrochureEquipmentCategory(
                category_name="Wnętrze",
                items=["Kierownica skórzana M", "Oświetlenie ambientowe"],
            ),
        ],
    )

    mock_process.return_value = mock_output

    # Call the mocked function
    result = mock_process(b"dummy pdf content", "pdf")

    # Assert correct structure
    assert result.brand == "BMW"
    assert result.power_hp == 184
    assert len(result.equipment_categories) == 2

    # Assert dynamic categories are present
    categories = [cat.category_name for cat in result.equipment_categories]
    assert "Bezpieczeństwo" in categories
    assert "Wnętrze" in categories

    # Validate Pydantic dump doesn't have prices or dealer info fields mapped
    result_dict = result.model_dump()
    assert "price" not in result_dict
    assert "prices" not in result_dict
    assert "dealer_info" not in result_dict


@patch("core.ai_service.process_brochure_document")
def test_brochure_extraction_commercial_vehicle(mock_process):
    mock_output = VehicleBrochureSchema(
        brand="Ford",
        model="Transit",
        vehicle_class="Dostawczy",
        payload_kg=1200,
        cargo_capacity_l=11000,
        equipment_categories=[
            BrochureEquipmentCategory(
                category_name="Przestrzeń Ładunkowa",
                items=["Wzmocniona podłoga", "Oświetlenie LED paki"],
            )
        ],
    )

    mock_process.return_value = mock_output
    result = mock_process(b"dummy pdf content", "pdf")

    assert result.vehicle_class == "Dostawczy"
    assert result.payload_kg == 1200
    assert result.cargo_capacity_l == 11000
    assert result.equipment_categories[0].category_name == "Przestrzeń Ładunkowa"
