import pytest
from core.samar_rv import SamarRVCalculator


class MockSettings:
    def __init__(self):
        self.samar_rv_apply_color_correction = True
        self.samar_rv_apply_body_correction = True
        self.samar_rv_apply_options_depreciation = True
        self.samar_rv_base_mileage = 140000
        self.samar_rv_mileage_unit_km = 10000


class MockInput:
    def __init__(self):
        self.settings = MockSettings()


@pytest.fixture
def mock_vehicle_data():
    return {
        "Segment": "B",
        "Paliwo": "Benzyna",  # Paliwo=1
        "MakeId": 55,  # Marka
        "ProdukcjaRok": 2020,
        "LakierRodzaj": "Metalik",
        "Zabudowa": "Furgon",
    }


@pytest.fixture
def mock_calc_input():
    return MockInput()


def test_map_fuel_type(mock_vehicle_data, mock_calc_input):
    calc = SamarRVCalculator(mock_vehicle_data, mock_calc_input)
    assert calc.fuel_type_id == 1  # Benzyna (PB) -> fuel_group_id=1

    mock_vehicle_data["Paliwo"] = "Diesel (ON)"
    calc = SamarRVCalculator(mock_vehicle_data, mock_calc_input)
    assert calc.fuel_type_id == 2  # Diesel (ON) -> fuel_group_id=2

    mock_vehicle_data["Paliwo"] = "Hybryda Plug-in (PHEV)"
    calc = SamarRVCalculator(mock_vehicle_data, mock_calc_input)
    assert calc.fuel_type_id == 3  # PHEV -> fuel_group_id=3


def test_samar_rv_calculate_base(mocker, mock_vehicle_data, mock_calc_input):
    """Testuje czy kalkulator wyliczy poprawnie RV wg uproszczonego V1 algorytmu na mockach"""
    mocker.patch.object(SamarRVCalculator, "get_base_rv_percentage", return_value=0.50)
    mocker.patch.object(SamarRVCalculator, "get_brand_correction", return_value=0.0)
    mocker.patch.object(
        SamarRVCalculator, "get_depreciation_correction", return_value=0.0
    )
    mocker.patch.object(SamarRVCalculator, "get_options_depreciation", return_value=0.8)
    mocker.patch.object(SamarRVCalculator, "get_color_correction", return_value=0.01)
    mocker.patch.object(SamarRVCalculator, "get_body_correction", return_value=0.02)
    mocker.patch.object(SamarRVCalculator, "get_vintage_correction", return_value=0.0)
    mocker.patch.object(
        SamarRVCalculator,
        "get_mileage_correction",
        return_value={"under_190": 0.0, "over_190": 0.0},
    )

    calc = SamarRVCalculator(mock_vehicle_data, mock_calc_input)

    # Base: 50%
    # Options: 80% (0.8)
    # Wartość 48 miesięcy = 50% * 100k = 50k
    # Brak deprecjacji
    # Opcje = 50k + (20k * 0.8) = 50k + 16k = 66k
    # Kolor = 100k * 0.01 = 1k
    # Zabudowa = 120k * 0.02 = 2.4k
    # RV = 66k + 1k + 2.4k = 69.4k

    rv_value = calc.calculate_rv(
        months=48, total_km=140000, base_vehicle_capex=100000.0, options_capex=20000.0
    )
    assert rv_value == pytest.approx(69400.0)


def test_samar_rv_sanity_bounds(mocker, mock_vehicle_data, mock_calc_input):
    """Sprawdzenie czy RV mieści się w granicach min 5% a max 95% łącznej ceny"""
    mocker.patch.object(SamarRVCalculator, "get_base_rv_percentage", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "get_brand_correction", return_value=0.0)
    mocker.patch.object(
        SamarRVCalculator, "get_depreciation_correction", return_value=0.0
    )
    mocker.patch.object(SamarRVCalculator, "get_options_depreciation", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "get_color_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "get_body_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "get_vintage_correction", return_value=0.0)
    mocker.patch.object(
        SamarRVCalculator,
        "get_mileage_correction",
        return_value={"under_190": 0.0, "over_190": 0.0},
    )

    calc = SamarRVCalculator(mock_vehicle_data, mock_calc_input)

    # Suma to 0%, powinno zostać podbite do 5% łącznej (100k + 20k = 120k * 0.05 = 6000)
    rv_value = calc.calculate_rv(
        months=48, total_km=140000, base_vehicle_capex=100000.0, options_capex=20000.0
    )
    assert rv_value == pytest.approx(6000.0)
